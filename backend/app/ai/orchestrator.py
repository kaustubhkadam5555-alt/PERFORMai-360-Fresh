import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMProvider, LLMUnavailableError
from app.ai.context_builder import EvidenceContext, EvidenceContextBuilder
from app.ai.prompts import ANALYSIS_PROMPT_VERSION, SYSTEM_INSTRUCTION, build_analysis_user_prompt
from app.ai.provider import MockLLMProvider, get_llm_provider
from app.ai.validators import validate_and_filter_citations
from app.schemas.review_analysis import (
    ContradictionItem,
    DiscussionQuestion,
    EvidenceAnalysisSummary,
    ImprovementOpportunity,
    ReviewAnalysisResponse,
    StrengthItem,
)

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Coordinates the end-to-end evidence review analysis pipeline:
    1. Authorized bounded evidence retrieval & context building
    2. Prompt construction with untrusted data isolation
    3. LLM generation (Mock, OpenAI, Anthropic, or Ollama)
    4. Post-generation citation verification & content sanitization
    5. Assembly of strongly typed ReviewAnalysisResponse
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def run_analysis(
        self,
        db: AsyncSession,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        source_type_filter: Optional[str] = None,
        max_evidence_items: Optional[int] = None,
        analysis_id: Optional[uuid.UUID] = None,
    ) -> ReviewAnalysisResponse:
        active_analysis_id = analysis_id or uuid.uuid4()
        timestamp = datetime.now(timezone.utc)

        # Step 1: Build bounded, verified evidence context
        builder = EvidenceContextBuilder(db)
        context: EvidenceContext = await builder.build_context(
            cycle_id=cycle_id,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            source_type_filter=source_type_filter,
            max_items=max_evidence_items,
        )

        dates = [item.source_date for item in context.evidence_items if item.source_date]
        earliest_date = min(dates) if dates else None
        latest_date = max(dates) if dates else None

        base_summary = EvidenceAnalysisSummary(
            total_evidence_examined=len(context.evidence_items),
            source_distribution=context.source_distribution,
            period_start=context.cycle.period_start,
            period_end=context.cycle.period_end,
            earliest_evidence_date=earliest_date,
            latest_evidence_date=latest_date,
            completeness_score=context.completeness_score,
            detected_gaps=context.detected_gaps,
            cited_evidence_ids=[],
        )

        # Step 2: Handle empty or insufficient evidence
        if len(context.evidence_items) == 0:
            logger.info("Insufficient evidence for cycle %s, employee %s", cycle_id, context.cycle.employee_id)
            return ReviewAnalysisResponse(
                analysis_id=active_analysis_id,
                cycle_id=cycle_id,
                employee_id=context.cycle.employee_id,
                status="insufficient_evidence",
                timestamp=timestamp,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                provider=self.provider.name,
                model=self.provider.model_name,
                evidence_summary=base_summary,
                strengths=[],
                improvement_opportunities=[],
                contradictions=[],
                suggested_discussion_questions=[
                    DiscussionQuestion(
                        category="evidence_gathering",
                        question="What key deliverables, pull requests, or project milestones were completed during this cycle?",
                        context="No verified evidence documents were present in the system for this review cycle.",
                    )
                ],
                overall_limitations=[
                    "No verified evidence records were found for this employee and cycle.",
                    "AI analysis cannot synthesize observations without grounded factual artifacts.",
                ],
                requires_human_review=True,
            )

        # Step 3: Verify provider availability
        if not self.provider.is_available:
            logger.warning("LLM provider '%s' is unavailable or disabled.", self.provider.name)
            return ReviewAnalysisResponse(
                analysis_id=active_analysis_id,
                cycle_id=cycle_id,
                employee_id=context.cycle.employee_id,
                status="failed",
                timestamp=timestamp,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                provider=self.provider.name,
                model=self.provider.model_name,
                evidence_summary=base_summary,
                strengths=[],
                improvement_opportunities=[],
                contradictions=[],
                suggested_discussion_questions=[],
                overall_limitations=[
                    f"LLM Provider '{self.provider.name}' is unavailable or unconfigured.",
                    "Please configure a valid provider (e.g. mock, openai, anthropic, ollama) or check credentials.",
                ],
                requires_human_review=True,
            )

        # Step 4: Inject context into Mock provider if applicable & build prompt
        if isinstance(self.provider, MockLLMProvider):
            self.provider.context = context

        user_prompt = build_analysis_user_prompt(context)
        try:
            raw_output = await self.provider.generate_analysis(
                prompt=user_prompt,
                system_instruction=SYSTEM_INSTRUCTION,
            )
        except (LLMUnavailableError, HTTPException) as e:
            detail = e.detail if isinstance(e, HTTPException) else str(e)
            logger.error("LLM Provider error: %s", detail)
            return ReviewAnalysisResponse(
                analysis_id=active_analysis_id,
                cycle_id=cycle_id,
                employee_id=context.cycle.employee_id,
                status="failed",
                timestamp=timestamp,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                provider=self.provider.name,
                model=self.provider.model_name,
                evidence_summary=base_summary,
                strengths=[],
                improvement_opportunities=[],
                contradictions=[],
                suggested_discussion_questions=[],
                overall_limitations=[f"Analysis generation failed: {detail}"],
                requires_human_review=True,
            )
        except Exception as e:
            logger.exception("Unexpected error during LLM generation: %s", str(e))
            return ReviewAnalysisResponse(
                analysis_id=active_analysis_id,
                cycle_id=cycle_id,
                employee_id=context.cycle.employee_id,
                status="failed",
                timestamp=timestamp,
                prompt_version=ANALYSIS_PROMPT_VERSION,
                provider=self.provider.name,
                model=self.provider.model_name,
                evidence_summary=base_summary,
                strengths=[],
                improvement_opportunities=[],
                contradictions=[],
                suggested_discussion_questions=[],
                overall_limitations=["Internal analysis generation error occurred."],
                requires_human_review=True,
            )

        # Step 5: Validate citations, filter hallucinations, sanitize content
        cleaned_data, warnings = validate_and_filter_citations(raw_output, context.valid_evidence_ids)

        # Collect all verified cited evidence IDs
        cited_ids: Set[uuid.UUID] = set()
        strengths: List[StrengthItem] = []
        for s in cleaned_data.get("strengths", []):
            st_item = StrengthItem(**s)
            strengths.append(st_item)
            cited_ids.update(st_item.supporting_evidence_ids)

        improvements: List[ImprovementOpportunity] = []
        for imp in cleaned_data.get("improvement_opportunities", []):
            imp_item = ImprovementOpportunity(**imp)
            improvements.append(imp_item)
            cited_ids.update(imp_item.supporting_evidence_ids)

        contradictions: List[ContradictionItem] = []
        for c in cleaned_data.get("contradictions", []):
            c_item = ContradictionItem(**c)
            contradictions.append(c_item)
            cited_ids.update(c_item.evidence_ids_a)
            cited_ids.update(c_item.evidence_ids_b)

        questions: List[DiscussionQuestion] = []
        for q in cleaned_data.get("suggested_discussion_questions", []):
            questions.append(DiscussionQuestion(**q))

        # Overall limitations
        limitations = list(cleaned_data.get("overall_limitations", []))
        if context.truncated:
            limitations.append("Source evidence was truncated to fit bounded context window limits.")

        final_summary = EvidenceAnalysisSummary(
            total_evidence_examined=len(context.evidence_items),
            source_distribution=context.source_distribution,
            period_start=context.cycle.period_start,
            period_end=context.cycle.period_end,
            earliest_evidence_date=earliest_date,
            latest_evidence_date=latest_date,
            completeness_score=context.completeness_score,
            detected_gaps=context.detected_gaps,
            cited_evidence_ids=sorted(list(cited_ids)),
        )

        return ReviewAnalysisResponse(
            analysis_id=active_analysis_id,
            cycle_id=cycle_id,
            employee_id=context.cycle.employee_id,
            status="completed",
            timestamp=timestamp,
            prompt_version=ANALYSIS_PROMPT_VERSION,
            provider=self.provider.name,
            model=self.provider.model_name,
            evidence_summary=final_summary,
            strengths=strengths,
            improvement_opportunities=improvements,
            contradictions=contradictions,
            suggested_discussion_questions=questions,
            overall_limitations=limitations,
            requires_human_review=True,
        )

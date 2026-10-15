import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import get_llm_provider
from app.models.review_cycle import ReviewCycle
from app.repositories.review_analysis_repository import ReviewAnalysisRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.schemas.review_analysis import (
    FindingResponse,
    ReviewAnalysisRequest,
    ReviewAnalysisResponse,
)

logger = logging.getLogger(__name__)


class ReviewAnalysisService:
    """
    Business service layer managing review analysis execution, persistence,
    findings extraction, and scoped authorization.
    """

    def __init__(self, db: AsyncSession, provider: Optional[LLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()
        self.orchestrator = AIOrchestrator(provider=self.provider)

    async def _verify_cycle_and_permissions(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReviewCycle:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        # Enforce viewer role and cross-employee isolation
        if viewer_role in {"admin", "administrator"}:
            return cycle

        if viewer_role == "manager":
            return cycle

        if viewer_id is not None:
            # Cycle owner or subject employee
            if cycle.owner_id == viewer_id or cycle.employee_id == viewer_id:
                return cycle
            # Unrelated employee
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have authorization to view or initiate analysis on this review cycle",
            )

        return cycle

    async def execute_analysis(
        self,
        cycle_id: uuid.UUID,
        request_in: Optional[ReviewAnalysisRequest] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReviewAnalysisResponse:
        """
        Orchestrates evidence review analysis, creates WorkflowRun audit trail,
        persists atomic Findings, and generates a draft ReviewReport.
        """
        cycle = await self._verify_cycle_and_permissions(cycle_id, viewer_id=viewer_id, viewer_role=viewer_role)

        req = request_in or ReviewAnalysisRequest()
        source_filter = req.source_type_filter
        max_items = req.max_evidence_items or 50

        # 1. Initialize persistent WorkflowRun
        run = await ReviewAnalysisRepository.create_workflow_run(
            db=self.db,
            cycle_id=cycle.id,
            workflow_status="in_progress",
            current_stage="evidence_analysis",
            stage_state={"source_filter": source_filter, "max_items": max_items},
            provider_metadata={"provider": self.provider.name, "model": self.provider.model_name},
        )

        try:
            # 2. Run analysis via AIOrchestrator
            analysis: ReviewAnalysisResponse = await self.orchestrator.run_analysis(
                db=self.db,
                cycle_id=cycle.id,
                viewer_id=viewer_id,
                viewer_role=viewer_role,
                source_type_filter=source_filter,
                max_evidence_items=max_items,
                analysis_id=run.id,
            )

            # 3. Update WorkflowRun status and outcome
            await ReviewAnalysisRepository.update_workflow_run(
                db=self.db,
                run=run,
                workflow_status=analysis.status,
                current_stage="analysis_completed" if analysis.status == "completed" else "analysis_insufficient",
                stage_state={
                    "evidence_examined": analysis.evidence_summary.total_evidence_examined,
                    "strengths_count": len(analysis.strengths),
                    "improvements_count": len(analysis.improvement_opportunities),
                    "contradictions_count": len(analysis.contradictions),
                },
                error_metadata={"limitations": analysis.overall_limitations} if analysis.overall_limitations else None,
            )

            # 4. Extract and persist discrete Finding records for granular tracking
            if analysis.status in {"completed", "insufficient_evidence"}:
                findings_payload: List[Dict[str, Any]] = []

                for s in analysis.strengths:
                    findings_payload.append(
                        {
                            "finding_type": "strength",
                            "statement": f"{s.title}: {s.description}",
                            "origin_type": "evidence_supported",
                            "evidence_ids": [str(eid) for eid in s.supporting_evidence_ids],
                            "limitations": s.limitations,
                            "validation_status": "validated" if s.supporting_evidence_ids else "unverified",
                        }
                    )

                for imp in analysis.improvement_opportunities:
                    findings_payload.append(
                        {
                            "finding_type": "improvement_opportunity",
                            "statement": f"{imp.title}: {imp.gap_observed} [Development: {imp.development_suggestion}]",
                            "origin_type": "gap_observation",
                            "evidence_ids": [str(eid) for eid in imp.supporting_evidence_ids],
                            "limitations": [imp.missing_context] if imp.missing_context else [],
                            "validation_status": "validated",
                        }
                    )

                for c in analysis.contradictions:
                    findings_payload.append(
                        {
                            "finding_type": "contradiction",
                            "statement": f"{c.topic}: (A) {c.observation_a} vs (B) {c.observation_b}",
                            "origin_type": "conflicting_signals",
                            "evidence_ids": [str(eid) for eid in c.evidence_ids_a + c.evidence_ids_b],
                            "limitations": [item for item in [c.missing_context, c.uncertainty_note] if item],
                            "validation_status": "flagged_for_review",
                        }
                    )

                if findings_payload:
                    await ReviewAnalysisRepository.bulk_create_findings(
                        db=self.db,
                        cycle_id=cycle.id,
                        findings_payloads=findings_payload,
                    )

            # 5. Persist draft ReviewReport if requested
            if req.include_draft_report and analysis.status in {"completed", "insufficient_evidence"}:
                await ReviewAnalysisRepository.create_or_update_report(
                    db=self.db,
                    cycle_id=cycle.id,
                    structured_content=analysis.model_dump(mode="json"),
                    generated_by_run_id=run.id,
                    created_by_id=viewer_id,
                    status="draft",
                )

            return analysis

        except Exception as exc:
            logger.exception("Failed executing review analysis for cycle %s: %s", cycle_id, exc)
            await ReviewAnalysisRepository.update_workflow_run(
                db=self.db,
                run=run,
                workflow_status="failed",
                current_stage="failed",
                error_metadata={"error": str(exc)},
            )
            raise

    async def get_analysis_by_id(
        self,
        cycle_id: uuid.UUID,
        analysis_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReviewAnalysisResponse:
        """
        Retrieves a persisted analysis run, validating cycle ownership and cross-cycle isolation.
        """
        cycle = await self._verify_cycle_and_permissions(cycle_id, viewer_id=viewer_id, viewer_role=viewer_role)

        run = await ReviewAnalysisRepository.get_workflow_run_by_id(self.db, analysis_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis with ID '{analysis_id}' not found",
            )

        # Enforce cross-cycle isolation
        if run.cycle_id != cycle.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis with ID '{analysis_id}' does not belong to review cycle '{cycle_id}'",
            )

        # Retrieve associated ReviewReport if present
        latest_report = await ReviewAnalysisRepository.get_latest_report_for_cycle(self.db, cycle.id)
        if latest_report and latest_report.generated_by_run_id == run.id and latest_report.structured_content:
            return ReviewAnalysisResponse(**latest_report.structured_content)

        # Reconstruct standard response from WorkflowRun state
        return ReviewAnalysisResponse(
            analysis_id=run.id,
            cycle_id=run.cycle_id,
            employee_id=cycle.employee_id,
            status=run.workflow_status,
            timestamp=run.created_at,
            prompt_version="v1.0",
            provider=(run.provider_metadata or {}).get("provider", "unknown"),
            model=(run.provider_metadata or {}).get("model", "unknown"),
            evidence_summary={
                "total_evidence_examined": (run.stage_state or {}).get("evidence_examined", 0),
                "source_distribution": {},
                "period_start": cycle.period_start,
                "period_end": cycle.period_end,
                "completeness_score": 0.0,
                "detected_gaps": [],
                "cited_evidence_ids": [],
            },
            strengths=[],
            improvement_opportunities=[],
            contradictions=[],
            suggested_discussion_questions=[],
            overall_limitations=(run.error_metadata or {}).get("limitations", []),
            requires_human_review=True,
        )

    async def get_latest_analysis_for_cycle(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> Optional[ReviewAnalysisResponse]:
        """Returns the latest ReviewReport analysis for the cycle, if available."""
        cycle = await self._verify_cycle_and_permissions(cycle_id, viewer_id=viewer_id, viewer_role=viewer_role)
        latest_report = await ReviewAnalysisRepository.get_latest_report_for_cycle(self.db, cycle.id)
        if not latest_report or not latest_report.structured_content:
            return None
        return ReviewAnalysisResponse(**latest_report.structured_content)

    async def list_findings_for_cycle(
        self,
        cycle_id: uuid.UUID,
        finding_type: Optional[str] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> List[FindingResponse]:
        """Returns atomic findings for the review cycle."""
        cycle = await self._verify_cycle_and_permissions(cycle_id, viewer_id=viewer_id, viewer_role=viewer_role)
        findings = await ReviewAnalysisRepository.list_findings_for_cycle(
            db=self.db, cycle_id=cycle.id, finding_type=finding_type
        )
        return [FindingResponse.model_validate(f) for f in findings]

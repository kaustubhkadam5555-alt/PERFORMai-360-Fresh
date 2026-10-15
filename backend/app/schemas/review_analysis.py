import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrengthItem(BaseModel):
    title: str = Field(..., description="Short descriptive title of the observed strength")
    description: str = Field(..., description="Evidence-grounded description of the contribution")
    supporting_evidence_ids: List[uuid.UUID] = Field(
        default_factory=list, description="IDs of verifiable evidence records supporting this observation"
    )
    excerpts: List[str] = Field(
        default_factory=list, description="Direct excerpts or bounded references from source evidence"
    )
    confidence: str = Field(default="high", description="Confidence level: high, medium, low")
    limitations: List[str] = Field(
        default_factory=list, description="Known context gaps or limitations affecting this observation"
    )

    model_config = ConfigDict(from_attributes=True)


class ImprovementOpportunity(BaseModel):
    title: str = Field(..., description="Neutral, behavior-focused development opportunity title")
    gap_observed: str = Field(..., description="Description of the observed development area")
    supporting_evidence_ids: List[uuid.UUID] = Field(
        default_factory=list, description="IDs of relevant evidence records (e.g. gap reports or tickets)"
    )
    missing_context: Optional[str] = Field(
        default=None, description="Context that could change the interpretation of this gap"
    )
    development_suggestion: str = Field(..., description="Actionable, constructive engineering growth suggestion")

    model_config = ConfigDict(from_attributes=True)


class ContradictionItem(BaseModel):
    topic: str = Field(..., description="Area of conflicting or ambiguous evidence")
    observation_a: str = Field(..., description="First perspective or positive signal")
    evidence_ids_a: List[uuid.UUID] = Field(default_factory=list, description="Evidence supporting first observation")
    observation_b: str = Field(..., description="Second perspective or contrasting signal")
    evidence_ids_b: List[uuid.UUID] = Field(default_factory=list, description="Evidence supporting second observation")
    missing_context: Optional[str] = Field(default=None, description="Information needed to reconcile the contrast")
    uncertainty_note: Optional[str] = Field(default=None, description="Explicit statement of evaluative uncertainty")

    model_config = ConfigDict(from_attributes=True)


class DiscussionQuestion(BaseModel):
    category: str = Field(..., description="Discussion theme: architecture, delivery, collaboration, growth")
    question: str = Field(..., description="Open-ended, non-accusatory question for review sync")
    context: str = Field(..., description="Why this question is recommended based on the evidence")

    model_config = ConfigDict(from_attributes=True)


class EvidenceAnalysisSummary(BaseModel):
    total_evidence_examined: int
    source_distribution: Dict[str, int] = Field(default_factory=dict)
    period_start: date
    period_end: date
    earliest_evidence_date: Optional[date] = None
    latest_evidence_date: Optional[date] = None
    completeness_score: float = 0.0
    detected_gaps: List[str] = Field(default_factory=list)
    cited_evidence_ids: List[uuid.UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReviewAnalysisRequest(BaseModel):
    source_type_filter: Optional[str] = Field(default=None, description="Optional filter by source type")
    max_evidence_items: Optional[int] = Field(default=50, ge=1, le=100, description="Max evidence items in context")
    include_draft_report: bool = Field(default=True, description="Whether to initialize or update a draft ReviewReport")


class ReviewAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    cycle_id: uuid.UUID
    employee_id: uuid.UUID
    status: str = Field(..., description="Analysis status: completed, insufficient_evidence, failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prompt_version: str = "v1.0"
    provider: str
    model: str
    evidence_summary: EvidenceAnalysisSummary
    strengths: List[StrengthItem] = Field(default_factory=list)
    improvement_opportunities: List[ImprovementOpportunity] = Field(default_factory=list)
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    suggested_discussion_questions: List[DiscussionQuestion] = Field(default_factory=list)
    overall_limitations: List[str] = Field(default_factory=list)
    requires_human_review: bool = True
    human_review_notice: str = (
        "This analysis is an evidence-grounded AI decision support draft. "
        "Consequential decisions must be made by authorized human managers and reviewers."
    )

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(BaseModel):
    id: uuid.UUID
    cycle_id: uuid.UUID
    finding_type: str
    statement: str
    origin_type: str
    evidence_ids: Optional[List[Any]] = None
    limitations: Optional[List[Any]] = None
    validation_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

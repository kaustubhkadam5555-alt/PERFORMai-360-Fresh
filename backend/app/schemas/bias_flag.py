import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BiasFlagBase(BaseModel):
    flag_type: str = Field(
        ...,
        description=(
            "Type of audit flag: evidence_coverage, recency_concentration, "
            "stakeholder_coverage, vague_or_absolute_claims, contradictory_feedback"
        ),
    )
    explanation: str = Field(..., description="Plain-language, non-accusatory explanation of the potential imbalance")
    severity: str = Field(default="review", description="Severity level: low, medium, high, review")
    evidence_ids: List[Any] = Field(default_factory=list, description="IDs of relevant or contrasting evidence records")
    suggested_action: Optional[str] = Field(None, description="Constructive, actionable reviewer recommendation")


class BiasFlagCreate(BiasFlagBase):
    cycle_id: uuid.UUID
    status: str = Field(default="open", description="Flag status: open, acknowledged, resolved, not_applicable")
    reviewer_comment: Optional[str] = None


class BiasFlagUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Updated status: open, acknowledged, resolved, not_applicable",
    )
    reviewer_comment: Optional[str] = Field(default=None, description="Reviewer justification or calibration comment")


class BiasFlagResponse(BiasFlagBase):
    id: uuid.UUID
    cycle_id: uuid.UUID
    status: str
    reviewer_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditExecutionRequest(BaseModel):
    rules_to_run: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific audit rules to execute. If omitted, runs all rules.",
    )
    re_evaluate_all: bool = Field(
        default=False,
        description="Whether to clear existing open flags before re-evaluating.",
    )


class AuditSummaryResponse(BaseModel):
    cycle_id: uuid.UUID
    total_flags: int
    open_flags: int
    acknowledged_flags: int
    resolved_flags: int
    not_applicable_flags: int
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
    flag_type_breakdown: Dict[str, int] = Field(default_factory=dict)
    audit_health_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calculated review quality and balance score (0.0 = severe imbalances, 1.0 = balanced & grounded)",
    )
    is_ready_for_review: bool = Field(
        ...,
        description="Indicates whether all high-severity flags have been acknowledged or resolved by reviewers",
    )
    flags: List[BiasFlagResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

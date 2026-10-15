import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class WorkflowStartRequest(BaseModel):
    """Payload to start a multi-agent review analysis workflow."""

    force_re_run: bool = Field(
        default=False,
        description="If True, initiates a new workflow run even if an existing active run exists.",
    )
    max_evidence_items: Optional[int] = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of evidence records to ingest for synthesis.",
    )


class WorkflowApprovalRequest(BaseModel):
    """Payload to record an authorized human manager approval."""

    comments: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional manager sign-off comments or review summary.",
    )


class WorkflowRevisionRequest(BaseModel):
    """Payload to request revisions from the multi-agent workflow."""

    revision_instructions: str = Field(
        ...,
        min_length=5,
        max_length=3000,
        description="Mandatory reviewer comments explaining the required revisions or additional evidence needed.",
    )


class WorkflowCancelRequest(BaseModel):
    """Payload to cancel an ongoing or paused workflow."""

    reason: Optional[str] = Field(
        default="Cancelled by user",
        max_length=500,
        description="Reason for cancelling the workflow run.",
    )


class WorkflowStageStatus(BaseModel):
    """Status details for an individual specialist agent or decision node."""

    stage_name: str
    display_title: str
    status: str = Field(..., description="pending, running, completed, failed, paused")
    description: str
    summary_data: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class WorkflowDraftReport(BaseModel):
    """Structured synthesized review report prepared by the ReviewSynthesisAgent."""

    cycle_id: str
    employee_id: str
    version_number: int = 1
    status: str = "draft"
    executive_summary: str
    strengths: List[Dict[str, Any]] = Field(default_factory=list)
    growth_areas: List[Dict[str, Any]] = Field(default_factory=list)
    goal_progress: List[Dict[str, Any]] = Field(default_factory=list)
    impact_highlights: List[Dict[str, Any]] = Field(default_factory=list)
    bias_audit_summary: Dict[str, Any] = Field(default_factory=dict)
    evidence_gaps_and_limitations: List[str] = Field(default_factory=list)
    suggested_discussion_questions: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class WorkflowStatusResponse(BaseModel):
    """Comprehensive status response for a multi-agent review workflow run."""

    run_id: uuid.UUID
    cycle_id: uuid.UUID
    employee_id: Optional[uuid.UUID] = None
    workflow_status: str = Field(
        ...,
        description="pending, running, awaiting_approval, approved, revision_requested, completed, failed, cancelled",
    )
    current_stage: Optional[str] = None
    stages: List[WorkflowStageStatus] = Field(default_factory=list)
    draft_report: Optional[WorkflowDraftReport] = None
    audit_health_score: Optional[float] = None
    is_ready_for_review: Optional[bool] = None
    audit_flags_count: int = 0
    available_actions: List[str] = Field(
        default_factory=list,
        description="List of legal actions the caller can execute given current state and role.",
    )
    approval_metadata: Optional[Dict[str, Any]] = None
    error_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    """List of workflow runs for a review cycle."""

    cycle_id: uuid.UUID
    total_count: int
    workflows: List[WorkflowStatusResponse]

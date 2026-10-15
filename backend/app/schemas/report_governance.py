import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SectionEditRequest(BaseModel):
    """Payload to edit a permitted section of a review report with optimistic concurrency."""

    content: Any = Field(..., description="New section content (string, list, or structured dictionary).")
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reviewer rationale or changelog summary for this edit.",
    )
    base_version_number: int = Field(
        ...,
        ge=1,
        description="Optimistic concurrency control: expected current version number before applying edit.",
    )


class ReportVersionSummary(BaseModel):
    """Summary of a specific immutable report version snapshot."""

    version_id: uuid.UUID
    report_id: uuid.UUID
    cycle_id: uuid.UUID
    version_number: int
    status: str
    changed_section: Optional[str] = None
    change_summary: Optional[str] = None
    author_id: Optional[uuid.UUID] = None
    author_role: Optional[str] = None
    is_ai_generated: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportVersionDetail(ReportVersionSummary):
    """Detailed view of an immutable report version snapshot including structured content."""

    structured_content: Dict[str, Any]


class ReportVersionListResponse(BaseModel):
    """List of all versions for a review report."""

    report_id: uuid.UUID
    cycle_id: uuid.UUID
    current_version_number: int
    total_versions: int
    versions: List[ReportVersionSummary]


class SectionDiffResult(BaseModel):
    """Deterministic diff between two versions for a specific report section."""

    section_key: str
    is_modified: bool
    diff_type: str = Field(..., description="'text', 'list', or 'object'")
    previous_value: Optional[Any] = None
    current_value: Optional[Any] = None
    added_items: List[Any] = Field(default_factory=list)
    removed_items: List[Any] = Field(default_factory=list)
    unified_diff: Optional[str] = None


class VersionComparisonResponse(BaseModel):
    """Comprehensive deterministic comparison between two report versions."""

    report_id: uuid.UUID
    cycle_id: uuid.UUID
    from_version_number: int
    to_version_number: int
    from_version_id: uuid.UUID
    to_version_id: uuid.UUID
    from_status: str
    to_status: str
    from_author_role: Optional[str] = None
    to_author_role: Optional[str] = None
    from_created_at: datetime
    to_created_at: datetime
    sections_changed: List[str]
    section_diffs: Dict[str, SectionDiffResult]
    added_citations: List[str] = Field(default_factory=list)
    removed_citations: List[str] = Field(default_factory=list)
    change_summary: List[str] = Field(default_factory=list)


class ReportApprovalRequest(BaseModel):
    """Payload to record an authorized human manager approval bound to an exact version."""

    version_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Exact version number to approve (stale approval prevention).",
    )
    version_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Exact version ID to approve.",
    )
    comments: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Reviewer approval comments or governance sign-off notes.",
    )


class ReportRevisionRequest(BaseModel):
    """Payload to request revisions on an exact report version."""

    version_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Expected version number when revision is requested.",
    )
    comments: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Mandatory reviewer instructions detailing required modifications or evidence.",
    )


class ApprovalRecordResponse(BaseModel):
    """Record of an explicit human approval or revision decision."""

    id: uuid.UUID
    report_id: uuid.UUID
    version_id: Optional[uuid.UUID] = None
    version_number: Optional[int] = None
    reviewer_id: uuid.UUID
    reviewer_name: Optional[str] = None
    reviewer_role: Optional[str] = None
    decision: str
    comments: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalHistoryResponse(BaseModel):
    """Collection of all approvals and decisions recorded for a report."""

    report_id: uuid.UUID
    cycle_id: uuid.UUID
    total_records: int
    approvals: List[ApprovalRecordResponse]


class GovernanceAuditEventResponse(BaseModel):
    """Immutable audit trail event record."""

    id: uuid.UUID
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GovernanceAuditListResponse(BaseModel):
    """Collection of governance audit events for an authorized report."""

    report_id: uuid.UUID
    cycle_id: uuid.UUID
    total_events: int
    events: List[GovernanceAuditEventResponse]


class ReportDetailResponse(BaseModel):
    """Comprehensive report details with latest content and governance metadata."""

    report_id: uuid.UUID
    cycle_id: uuid.UUID
    employee_id: uuid.UUID
    version_number: int
    status: str
    structured_content: Dict[str, Any]
    latest_version_id: Optional[uuid.UUID] = None
    is_approved: bool = False
    approved_version_number: Optional[int] = None
    last_approved_at: Optional[datetime] = None
    last_edited_by: Optional[str] = None
    last_edited_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

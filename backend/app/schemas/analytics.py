import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_cycles: int = Field(..., description="Total review cycles in system or scope")
    cycles_by_status: Dict[str, int] = Field(default_factory=dict, description="Cycle count broken down by status")
    total_reports: int = Field(..., description="Total review reports generated")
    reports_by_status: Dict[str, int] = Field(default_factory=dict, description="Report count broken down by status")
    completion_rate: float = Field(..., description="Review completion percentage (0.0 - 100.0)")
    completion_numerator: int = Field(..., description="Completed cycles or approved reports")
    completion_denominator: int = Field(..., description="Total target cycles")
    completion_definition: str = Field(
        default="Percentage of review cycles that have completed reviews with finalized approvals",
        description="Explicit description of how completion rate was calculated",
    )
    total_evidence_items: int = Field(..., description="Total ingested evidence records")
    total_feedback_items: int = Field(..., description="Total 360-degree feedback responses")
    total_goals: int = Field(default=0, description="Total tracked goals")
    total_approvals: int = Field(default=0, description="Total manager approval decisions recorded")
    approvals_by_decision: Dict[str, int] = Field(
        default_factory=dict, description="Approved vs Revision Requested count"
    )
    average_audit_health_score: Optional[float] = Field(None, description="System-wide average bias audit health score")
    total_bias_flags: int = Field(default=0, description="Total deterministic bias/quality audit flags raised")


class CycleAnalyticsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cycle_id: uuid.UUID
    title: str
    employee_name: Optional[str] = None
    status: str
    evidence_count: int
    feedback_count: int
    report_version: Optional[int] = None
    report_status: Optional[str] = None
    audit_health_score: Optional[float] = None


class ReviewAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_cycles: int
    status_distribution: Dict[str, int]
    completed_count: int
    in_progress_count: int
    completion_rate: float
    average_duration_days: Optional[float] = None
    cycles: List[CycleAnalyticsItem] = Field(default_factory=list)


class EvidenceAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_evidence_items: int
    source_type_distribution: Dict[str, int] = Field(default_factory=dict)
    access_policy_distribution: Dict[str, int] = Field(default_factory=dict)
    total_citations_in_reports: int = 0
    supported_claims_count: int = 0
    ungrounded_claims_flag_count: int = 0
    overall_coverage_percentage: float = 0.0


class AuditAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_flags: int
    flags_by_rule: Dict[str, int] = Field(default_factory=dict)
    flags_by_severity: Dict[str, int] = Field(default_factory=dict)
    flags_by_status: Dict[str, int] = Field(default_factory=dict)
    average_health_score: float = 100.0
    score_distribution: Dict[str, int] = Field(default_factory=dict)


class TrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_label: str
    cycles_created: int = 0
    reports_approved: int = 0
    evidence_uploaded: int = 0
    feedback_submitted: int = 0
    bias_flags_raised: int = 0


class AnalyticsTrendsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interval: str = "month"
    total_points: int = 0
    trends: List[TrendPoint] = Field(default_factory=list)

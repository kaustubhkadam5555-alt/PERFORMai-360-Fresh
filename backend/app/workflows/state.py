from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class MultiAgentWorkflowState(TypedDict, total=False):
    """
    Explicit, typed state for the PERFORMai-360 LangGraph multi-agent workflow.
    Guarantees that state transitions are safe, validated, and serialized.
    """

    # Identifiers & Access Scoping
    run_id: str
    cycle_id: str
    employee_id: str
    initiating_user_id: Optional[str]
    initiating_user_role: Optional[str]

    # Workflow Execution Status
    status: str  # pending, running, awaiting_approval, approved, revision_requested, completed, failed, cancelled
    current_stage: str
    max_evidence_items: int

    # 1. EvidenceRetrievalAgent Output
    evidence_items: List[Dict[str, Any]]
    evidence_count: int
    source_distribution: Dict[str, int]
    evidence_gaps: List[str]
    evidence_completeness_score: float
    retrieval_status: str

    # 2. FeedbackAnalysisAgent Output
    feedback_findings: List[Dict[str, Any]]
    strengths: List[Dict[str, Any]]
    improvement_opportunities: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    missing_perspectives: List[str]
    discussion_questions: List[str]
    analysis_status: str

    # 3. BiasAuditorAgent Output
    audit_health_score: float
    is_ready_for_review: bool
    audit_flags: List[Dict[str, Any]]
    severity_breakdown: Dict[str, int]
    flag_type_breakdown: Dict[str, int]
    audit_status: str

    # 4. ReviewSynthesisAgent Output
    draft_report: Dict[str, Any]
    synthesis_status: str

    # 5. HumanApprovalPauseNode & Decisions
    approval_decision: Optional[str]  # approved, revision_requested, cancelled
    reviewer_id: Optional[str]
    reviewer_role: Optional[str]
    reviewer_comments: Optional[str]
    approval_timestamp: Optional[str]

    # Finalization & Execution Metadata
    final_report_id: Optional[str]
    errors: List[str]
    retry_count: int
    stage_durations: Dict[str, float]
    created_at: str
    updated_at: str

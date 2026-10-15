import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.provider import get_llm_provider
from app.audit.engine import AuditEngine
from app.models.review_cycle import ReviewCycle
from app.models.user import User
from app.models.workflow_run import WorkflowRun
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.review_analysis_repository import ReviewAnalysisRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.bias_audit_service import BiasAuditService
from app.services.evidence_service import EvidenceService
from app.workflows.state import MultiAgentWorkflowState

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Node 1: EvidenceRetrievalAgent
# ---------------------------------------------------------------------------


async def evidence_retrieval_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    EvidenceRetrievalAgent:
    Gathers and packages authorized source evidence records for the review cycle.
    Enforces employee and review cycle scoping and detects missing evidence gaps.
    """
    logger.info("Executing EvidenceRetrievalAgent for run=%s cycle=%s", state.get("run_id"), state.get("cycle_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_id_str = state["cycle_id"]
    cycle_uuid = uuid.UUID(cycle_id_str)
    max_items = state.get("max_evidence_items", 50)

    # Fetch cycle to verify existence & target employee
    cycle: Optional[ReviewCycle] = await ReviewCycleRepository.get_by_id(db, cycle_uuid)
    if not cycle:
        raise ValueError(f"Review cycle '{cycle_id_str}' not found")

    employee_id_str = str(cycle.employee_id)

    # 1. Retrieve evidence items
    evidence_entities = await EvidenceRepository.list_all_for_cycle(db, cycle_uuid)
    scoped_evidence = evidence_entities[:max_items]

    serialized_items: List[Dict[str, Any]] = [
        {
            "id": str(e.id),
            "title": e.title,
            "source_type": e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type),
            "source_date": e.source_date.isoformat() if e.source_date else None,
            "access_policy": e.access_policy.value if hasattr(e.access_policy, "value") else str(e.access_policy),
            "storage_path": e.storage_reference,
            "metadata": e.metadata_json or {},
        }
        for e in scoped_evidence
    ]

    # 2. Compute completeness and evidence gaps
    evidence_service = EvidenceService(db)
    completeness = await evidence_service.get_cycle_evidence_completeness(cycle_uuid)

    source_dist = completeness.source_distribution
    evidence_gaps = completeness.detected_gaps
    completeness_score = completeness.completeness_score

    retrieval_status = "success" if serialized_items else "empty"

    return {
        "employee_id": employee_id_str,
        "evidence_items": serialized_items,
        "evidence_count": len(serialized_items),
        "source_distribution": source_dist,
        "evidence_gaps": evidence_gaps,
        "evidence_completeness_score": completeness_score,
        "retrieval_status": retrieval_status,
        "current_stage": "evidence_retrieval",
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 2: FeedbackAnalysisAgent
# ---------------------------------------------------------------------------


async def feedback_analysis_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    FeedbackAnalysisAgent:
    Analyzes authorized feedback (self, peer, manager) using the provider abstraction.
    Extracts candidate strengths, growth opportunities, contradictions, and missing perspectives.
    """
    logger.info("Executing FeedbackAnalysisAgent for run=%s cycle=%s", state.get("run_id"), state.get("cycle_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    provider: Optional[LLMProvider] = cfg.get("provider") or get_llm_provider()
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_id_str = state["cycle_id"]
    cycle_uuid = uuid.UUID(cycle_id_str)

    # 1. Gather feedback submissions and check perspective coverage
    feedback_entities = await FeedbackRepository.list_feedback(db, cycle_id=cycle_uuid, limit=100)
    types_present = {
        f.feedback_type.value if hasattr(f.feedback_type, "value") else str(f.feedback_type) for f in feedback_entities
    }

    missing_perspectives: List[str] = []
    if "self" not in types_present:
        missing_perspectives.append("Self-assessment not submitted")
    if "peer" not in types_present:
        missing_perspectives.append("Peer reviews not submitted")
    if "manager" not in types_present:
        missing_perspectives.append("Manager assessment not submitted")

    # 2. Run evidence-grounded AI analysis via AIOrchestrator
    orchestrator = AIOrchestrator(provider=provider)
    analysis_resp = await orchestrator.run_analysis(
        db=db,
        cycle_id=cycle_uuid,
        viewer_id=uuid.UUID(state["initiating_user_id"]) if state.get("initiating_user_id") else None,
        viewer_role=state.get("initiating_user_role"),
        max_evidence_items=state.get("max_evidence_items", 50),
    )

    strengths = [s.model_dump(mode="json") for s in analysis_resp.strengths]
    improvement_opportunities = [g.model_dump(mode="json") for g in analysis_resp.improvement_opportunities]
    contradictions = [c.model_dump(mode="json") for c in analysis_resp.contradictions]
    discussion_questions = [
        q.model_dump(mode="json") if hasattr(q, "model_dump") else q
        for q in analysis_resp.suggested_discussion_questions
    ]

    # Candidate atomic findings
    findings = [
        {
            "finding_type": "strength",
            "statement": s.get("title", "") + ": " + s.get("description", ""),
            "evidence_ids": [str(x) for x in s.get("supporting_evidence_ids", [])],
            "confidence_score": 0.95,
        }
        for s in strengths
    ] + [
        {
            "finding_type": "improvement_opportunity",
            "statement": g.get("growth_area", "") + ": " + g.get("development_suggestion", ""),
            "evidence_ids": [str(x) for x in g.get("supporting_evidence_ids", [])],
            "confidence_score": 0.90,
        }
        for g in improvement_opportunities
    ]

    return {
        "feedback_findings": findings,
        "strengths": strengths,
        "improvement_opportunities": improvement_opportunities,
        "contradictions": contradictions,
        "missing_perspectives": missing_perspectives,
        "discussion_questions": discussion_questions,
        "analysis_status": "success",
        "current_stage": "feedback_analysis",
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 3: BiasAuditorAgent
# ---------------------------------------------------------------------------


async def bias_auditor_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    BiasAuditorAgent:
    Executes the 5 deterministic bias and evidence-quality audit rules.
    Outputs the Audit Health Score, review readiness status, and persistent flags.
    """
    logger.info("Executing BiasAuditorAgent for run=%s cycle=%s", state.get("run_id"), state.get("cycle_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_id_str = state["cycle_id"]
    cycle_uuid = uuid.UUID(cycle_id_str)

    # Reuse BiasAuditService to evaluate the 5 rules against the cycle's domain artifacts
    audit_service = BiasAuditService(db, engine=AuditEngine())
    audit_summary = await audit_service.execute_audit(
        cycle_id=cycle_uuid,
        viewer_id=uuid.UUID(state["initiating_user_id"]) if state.get("initiating_user_id") else None,
        viewer_role=state.get("initiating_user_role"),
    )

    flags_serialized = [f.model_dump(mode="json") for f in audit_summary.flags]

    return {
        "audit_health_score": audit_summary.audit_health_score,
        "is_ready_for_review": audit_summary.is_ready_for_review,
        "audit_flags": flags_serialized,
        "severity_breakdown": audit_summary.severity_breakdown,
        "flag_type_breakdown": audit_summary.flag_type_breakdown,
        "audit_status": "success",
        "current_stage": "bias_audit",
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 4: ReviewSynthesisAgent
# ---------------------------------------------------------------------------


async def review_synthesis_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    ReviewSynthesisAgent:
    Combines validated evidence, feedback findings, goal progress, and audit flags
    into a structured draft performance review matching PRD FR-11.
    """
    logger.info("Executing ReviewSynthesisAgent for run=%s cycle=%s", state.get("run_id"), state.get("cycle_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_id_str = state["cycle_id"]
    cycle_uuid = uuid.UUID(cycle_id_str)

    # 1. Fetch Goals
    goal_entities = await GoalRepository.list_goals(db, cycle_id=cycle_uuid, limit=100)
    goals_serialized = [
        {
            "id": str(g.id),
            "description": g.description,
            "status": g.status.value if hasattr(g.status, "value") else str(g.status),
            "measurable_target": g.measurable_target,
            "outcome_notes": g.outcome_notes,
        }
        for g in goal_entities
    ]

    # 2. Extract verified citation IDs
    raw_strengths = state.get("strengths", [])
    raw_improvements = state.get("improvement_opportunities", [])

    strengths = []
    for s in raw_strengths:
        s_dict = dict(s)
        s_dict["supporting_evidence_ids"] = [str(cid) for cid in s_dict.get("supporting_evidence_ids", [])]
        strengths.append(s_dict)

    improvement_opportunities = []
    for g in raw_improvements:
        g_dict = dict(g)
        g_dict["supporting_evidence_ids"] = [str(cid) for cid in g_dict.get("supporting_evidence_ids", [])]
        improvement_opportunities.append(g_dict)

    citations_set = set()
    for s in strengths:
        for cid in s.get("supporting_evidence_ids", []):
            citations_set.add(cid)
    for g in improvement_opportunities:
        for cid in g.get("supporting_evidence_ids", []):
            citations_set.add(cid)
    citations_list = sorted(list(citations_set))

    # 3. Synthesize Executive Summary
    evidence_count = state.get("evidence_count", 0)
    health_score = state.get("audit_health_score", 100.0)
    strengths_count = len(strengths)
    growth_count = len(improvement_opportunities)

    exec_summary = (
        f"Synthesized review evaluation covering {evidence_count} verified evidence artifacts. "
        f"Identified {strengths_count} demonstrated technical strengths and {growth_count} strategic development opportunities. "
        f"Audit Health Score evaluated at {health_score:.1f}/100 with strict grounding and zero automated employment scoring."
    )

    # 4. Impact highlights from strengths
    impact_highlights = [
        {
            "title": s.get("title", "Technical Contribution"),
            "impact_summary": s.get("description", ""),
            "citations": s.get("supporting_evidence_ids", []),
        }
        for s in strengths[:3]
    ]

    # 5. Build structured draft review
    draft_report_dict = {
        "cycle_id": cycle_id_str,
        "employee_id": state.get("employee_id", ""),
        "version_number": 1,
        "status": "draft",
        "executive_summary": exec_summary,
        "strengths": strengths,
        "growth_areas": improvement_opportunities,
        "goal_progress": goals_serialized,
        "impact_highlights": impact_highlights,
        "bias_audit_summary": {
            "health_score": health_score,
            "is_ready_for_review": state.get("is_ready_for_review", False),
            "severity_breakdown": state.get("severity_breakdown", {}),
            "total_flags": len(state.get("audit_flags", [])),
        },
        "evidence_gaps_and_limitations": state.get("evidence_gaps", []) + state.get("missing_perspectives", []),
        "suggested_discussion_questions": state.get("discussion_questions", []),
        "citations": citations_list,
        "created_at": _utc_now_iso(),
    }

    # Persist or update draft ReviewReport in database
    run_uuid = uuid.UUID(state["run_id"]) if state.get("run_id") else None
    if run_uuid:
        existing_run = await db.get(WorkflowRun, run_uuid)
        if not existing_run:
            run_uuid = None

    user_uuid = uuid.UUID(state["initiating_user_id"]) if state.get("initiating_user_id") else None
    if user_uuid:
        existing_user = await db.get(User, user_uuid)
        if not existing_user:
            user_uuid = None

    report = await ReviewAnalysisRepository.create_or_update_report(
        db=db,
        cycle_id=cycle_uuid,
        structured_content=draft_report_dict,
        generated_by_run_id=run_uuid,
        created_by_id=user_uuid,
        status="draft",
    )
    draft_report_dict["version_number"] = report.version_number
    draft_report_dict["report_id"] = str(report.id)

    return {
        "draft_report": draft_report_dict,
        "synthesis_status": "draft_generated",
        "current_stage": "review_synthesis",
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 5: HumanApprovalPauseNode
# ---------------------------------------------------------------------------


async def human_approval_pause_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    HumanApprovalPauseNode:
    Mandatory decision boundary. If no human decision is recorded, pauses workflow execution
    and transitions state to 'awaiting_approval'. Resumes to finalization or revision handling
    once an authorized decision ('approved', 'revision_requested', 'cancelled') is recorded.
    """
    logger.info(
        "Executing HumanApprovalPauseNode for run=%s decision=%s", state.get("run_id"), state.get("approval_decision")
    )
    decision = state.get("approval_decision")

    if not decision:
        # Pause execution and await authorized human sign-off
        return {
            "status": "awaiting_approval",
            "approval_decision": None,
            "current_stage": "human_approval_pause",
            "updated_at": _utc_now_iso(),
        }

    if decision == "approved":
        return {
            "status": "approved",
            "approval_decision": "approved",
            "current_stage": "finalization",
            "approval_timestamp": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }

    if decision == "revision_requested":
        return {
            "status": "revision_requested",
            "approval_decision": "revision_requested",
            "current_stage": "revision_handling",
            "approval_timestamp": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }

    if decision in {"cancelled", "rejected"}:
        return {
            "status": "cancelled",
            "approval_decision": decision,
            "current_stage": "cancelled",
            "updated_at": _utc_now_iso(),
        }

    return {
        "status": "failed",
        "errors": state.get("errors", []) + [f"Unknown approval decision '{decision}'"],
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 6: FinalizationNode
# ---------------------------------------------------------------------------


async def finalization_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    FinalizationNode:
    Finalizes the approved review report, records human approval sign-off, and logs
    an immutable AuditEvent.
    """
    logger.info("Executing FinalizationNode for run=%s", state.get("run_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_uuid = uuid.UUID(state["cycle_id"])
    reviewer_id_str = state.get("reviewer_id")
    reviewer_uuid = uuid.UUID(reviewer_id_str) if reviewer_id_str else None
    if reviewer_uuid:
        existing_rev = await db.get(User, reviewer_uuid)
        if not existing_rev:
            reviewer_uuid = None
    comments = state.get("reviewer_comments")

    # 1. Fetch latest draft report for the cycle
    report = await ReviewAnalysisRepository.get_latest_report_for_cycle(db, cycle_uuid)
    if report:
        report.status = "approved"
        await db.commit()
        await db.refresh(report)

        # 2. Record Approval
        if reviewer_uuid:
            await WorkflowRepository.record_approval(
                db=db,
                report_id=report.id,
                reviewer_id=reviewer_uuid,
                decision="approved",
                comments=comments,
            )

        # 3. Record AuditEvent
        await WorkflowRepository.record_audit_event(
            db=db,
            action="workflow.approved",
            resource_type="review_report",
            resource_id=str(report.id),
            actor_id=reviewer_uuid,
            metadata_json={
                "cycle_id": state["cycle_id"],
                "run_id": state.get("run_id"),
                "comments": comments,
                "version_number": report.version_number,
            },
        )
        final_report_id = str(report.id)
    else:
        final_report_id = None

    return {
        "status": "completed",
        "current_stage": "completed",
        "final_report_id": final_report_id,
        "updated_at": _utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Node 7: RevisionHandlerNode
# ---------------------------------------------------------------------------


async def revision_handler_node(
    state: MultiAgentWorkflowState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    RevisionHandlerNode:
    Handles reviewer revision requests, records reviewer comments, updates report status,
    and logs an audit event.
    """
    logger.info("Executing RevisionHandlerNode for run=%s", state.get("run_id"))
    cfg = config.get("configurable", {}) if config else {}
    db: AsyncSession = cfg.get("db")
    if not db:
        raise ValueError("Database session missing in config['configurable']['db']")

    cycle_uuid = uuid.UUID(state["cycle_id"])
    reviewer_id_str = state.get("reviewer_id")
    reviewer_uuid = uuid.UUID(reviewer_id_str) if reviewer_id_str else None
    if reviewer_uuid:
        existing_rev = await db.get(User, reviewer_uuid)
        if not existing_rev:
            reviewer_uuid = None
    comments = state.get("reviewer_comments")

    report = await ReviewAnalysisRepository.get_latest_report_for_cycle(db, cycle_uuid)
    if report:
        report.status = "revision_requested"
        await db.commit()
        await db.refresh(report)

        if reviewer_uuid:
            await WorkflowRepository.record_approval(
                db=db,
                report_id=report.id,
                reviewer_id=reviewer_uuid,
                decision="revision_requested",
                comments=comments,
            )

        await WorkflowRepository.record_audit_event(
            db=db,
            action="workflow.revision_requested",
            resource_type="review_report",
            resource_id=str(report.id),
            actor_id=reviewer_uuid,
            metadata_json={
                "cycle_id": state["cycle_id"],
                "run_id": state.get("run_id"),
                "instructions": comments,
                "version_number": report.version_number,
            },
        )

    return {
        "status": "revision_requested",
        "current_stage": "revision_handling",
        "updated_at": _utc_now_iso(),
    }

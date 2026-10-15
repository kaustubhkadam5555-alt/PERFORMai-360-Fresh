import uuid
from datetime import date

import pytest
from langgraph.graph import END
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence, EvidenceAccessPolicy, EvidenceSourceType
from app.models.feedback import Feedback, FeedbackType, FeedbackVisibility
from app.models.goal import Goal, GoalStatus
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.user import User, UserRole
from app.workflows.graph import build_workflow_graph, route_after_human_pause
from app.workflows.nodes import (
    bias_auditor_node,
    evidence_retrieval_node,
    feedback_analysis_node,
    finalization_node,
    human_approval_pause_node,
    review_synthesis_node,
    revision_handler_node,
)
from app.workflows.state import MultiAgentWorkflowState


@pytest.fixture
async def cycle_setup(db_session: AsyncSession):
    manager = User(
        full_name="Engineering Manager",
        email=f"manager_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    employee = User(
        full_name="Staff Engineer",
        email=f"employee_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([manager, employee])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(employee)

    cycle = ReviewCycle(
        title="Q3 Technical Review",
        owner_id=manager.id,
        employee_id=employee.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 9, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    # Add evidence
    evidence = Evidence(
        cycle_id=cycle.id,
        source_type=EvidenceSourceType.PR,
        title="PR #101: Distributed Consensus Implementation",
        source_date=date(2026, 7, 20),
        storage_reference="safe/path/pr_101.txt",
        access_policy=EvidenceAccessPolicy.INTERNAL,
    )
    # Add feedback
    feedback = Feedback(
        cycle_id=cycle.id,
        author_id=manager.id,
        subject_employee_id=employee.id,
        feedback_type=FeedbackType.MANAGER,
        visibility=FeedbackVisibility.SHARED,
        content="Outstanding technical leadership on the distributed consensus project.",
    )
    # Add goal
    goal = Goal(
        cycle_id=cycle.id,
        description="Ship consensus engine with 99.99% reliability",
        status=GoalStatus.COMPLETED,
    )
    db_session.add_all([evidence, feedback, goal])
    await db_session.commit()
    await db_session.refresh(evidence)

    return {"cycle": cycle, "manager": manager, "employee": employee, "evidence": evidence}


@pytest.mark.asyncio
async def test_evidence_retrieval_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "max_evidence_items": 50,
    }
    config = {"configurable": {"db": db_session}}

    result = await evidence_retrieval_node(state, config=config)

    assert result["evidence_count"] >= 1
    assert result["retrieval_status"] == "success"
    assert "PR #101" in result["evidence_items"][0]["title"]
    assert result["current_stage"] == "evidence_retrieval"


@pytest.mark.asyncio
async def test_feedback_analysis_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "initiating_user_id": str(cycle_setup["manager"].id),
        "initiating_user_role": "manager",
        "max_evidence_items": 50,
    }
    config = {"configurable": {"db": db_session}}

    result = await feedback_analysis_node(state, config=config)

    assert result["analysis_status"] == "success"
    assert len(result["strengths"]) >= 1
    assert "Self-assessment not submitted" in result["missing_perspectives"]
    assert result["current_stage"] == "feedback_analysis"


@pytest.mark.asyncio
async def test_bias_auditor_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "initiating_user_id": str(cycle_setup["manager"].id),
        "initiating_user_role": "manager",
    }
    config = {"configurable": {"db": db_session}}

    result = await bias_auditor_node(state, config=config)

    assert result["audit_status"] == "success"
    assert isinstance(result["audit_health_score"], float)
    assert "severity_breakdown" in result
    assert result["current_stage"] == "bias_audit"


@pytest.mark.asyncio
async def test_review_synthesis_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    evidence = cycle_setup["evidence"]
    state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "initiating_user_id": str(cycle_setup["manager"].id),
        "strengths": [
            {
                "title": "Consensus Engineering",
                "description": "Implemented zero-data-loss consensus",
                "supporting_evidence_ids": [str(evidence.id)],
            }
        ],
        "improvement_opportunities": [],
        "audit_health_score": 95.0,
        "is_ready_for_review": True,
        "evidence_count": 1,
        "evidence_gaps": [],
        "missing_perspectives": ["Self-assessment not submitted"],
        "discussion_questions": ["What went well in Q3?"],
    }
    config = {"configurable": {"db": db_session}}

    result = await review_synthesis_node(state, config=config)

    assert result["synthesis_status"] == "draft_generated"
    draft = result["draft_report"]
    assert draft["status"] == "draft"
    assert str(evidence.id) in draft["citations"]
    assert "Consensus Engineering" in draft["strengths"][0]["title"]
    assert len(draft["goal_progress"]) >= 1


@pytest.mark.asyncio
async def test_human_approval_pause_and_routing():
    # 1. No decision recorded -> Pauses
    state_no_decision: MultiAgentWorkflowState = {"approval_decision": None}
    pause_res = await human_approval_pause_node(state_no_decision)
    assert pause_res["status"] == "awaiting_approval"
    assert pause_res["current_stage"] == "human_approval_pause"
    assert route_after_human_pause(pause_res) == END

    # 2. Approved decision recorded -> Routes to finalization
    state_approved: MultiAgentWorkflowState = {"approval_decision": "approved"}
    approved_res = await human_approval_pause_node(state_approved)
    assert approved_res["status"] == "approved"
    assert route_after_human_pause(approved_res) == "finalization"

    # 3. Revision requested recorded -> Routes to revision_handler
    state_revision: MultiAgentWorkflowState = {"approval_decision": "revision_requested"}
    rev_res = await human_approval_pause_node(state_revision)
    assert rev_res["status"] == "revision_requested"
    assert route_after_human_pause(rev_res) == "revision_handler"


@pytest.mark.asyncio
async def test_full_graph_execution_up_to_pause(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    manager = cycle_setup["manager"]
    graph = build_workflow_graph()

    initial_state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "initiating_user_id": str(manager.id),
        "initiating_user_role": "manager",
        "max_evidence_items": 50,
        "errors": [],
    }
    config = {"configurable": {"db": db_session}}

    final_state = await graph.ainvoke(initial_state, config=config)

    # Workflow must execute all 4 agents and PAUSE at HumanApprovalPauseNode
    assert final_state["status"] == "awaiting_approval"
    assert final_state["current_stage"] == "human_approval_pause"
    assert final_state["evidence_count"] >= 1
    assert len(final_state["strengths"]) >= 1
    assert final_state["draft_report"]["status"] == "draft"
    assert final_state["approval_decision"] is None


@pytest.mark.asyncio
async def test_finalization_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    manager = cycle_setup["manager"]

    # First synthesize a draft report
    state: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "employee_id": str(cycle.employee_id),
        "initiating_user_id": str(manager.id),
        "strengths": [],
        "improvement_opportunities": [],
    }
    config = {"configurable": {"db": db_session}}
    await review_synthesis_node(state, config=config)

    # Execute finalization
    final_input: MultiAgentWorkflowState = {
        "run_id": state["run_id"],
        "cycle_id": str(cycle.id),
        "approval_decision": "approved",
        "reviewer_id": str(manager.id),
        "reviewer_comments": "Approved without objections. Exemplary work.",
    }
    fin_res = await finalization_node(final_input, config=config)

    assert fin_res["status"] == "completed"
    assert fin_res["current_stage"] == "completed"
    assert fin_res["final_report_id"] is not None


@pytest.mark.asyncio
async def test_revision_handler_node(db_session: AsyncSession, cycle_setup):
    cycle = cycle_setup["cycle"]
    manager = cycle_setup["manager"]
    config = {"configurable": {"db": db_session}}

    rev_input: MultiAgentWorkflowState = {
        "run_id": str(uuid.uuid4()),
        "cycle_id": str(cycle.id),
        "approval_decision": "revision_requested",
        "reviewer_id": str(manager.id),
        "reviewer_comments": "Please include performance data from the benchmarking test suite.",
    }
    rev_res = await revision_handler_node(rev_input, config=config)

    assert rev_res["status"] == "revision_requested"
    assert rev_res["current_stage"] == "revision_handling"

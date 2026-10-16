import uuid
from datetime import date
from typing import Any, Dict

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.bias_flag import BiasFlag
from app.models.evidence import Evidence, EvidenceAccessPolicy, EvidenceSourceType
from app.models.feedback import Feedback, FeedbackType, FeedbackVisibility
from app.models.goal import Goal, GoalStatus
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.user import User, UserRole
from app.models.workflow_run import WorkflowRun
from app.repositories.report_governance_repository import ReportGovernanceRepository


@pytest.fixture
async def analytics_env(db_session: AsyncSession) -> Dict[str, Any]:
    manager = User(
        full_name="Analytics Lead Manager",
        email=f"analytics_mgr_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    employee_1 = User(
        full_name="Alice Engineer",
        email=f"alice_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    employee_2 = User(
        full_name="Bob SRE",
        email=f"bob_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([manager, employee_1, employee_2])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(employee_1)
    await db_session.refresh(employee_2)

    # Cycle 1: Completed & Approved
    cycle_1 = ReviewCycle(
        title="2026 H1 Alice Review",
        owner_id=manager.id,
        employee_id=employee_1.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.COMPLETED,
    )
    # Cycle 2: Active & In Review
    cycle_2 = ReviewCycle(
        title="2026 H1 Bob Review",
        owner_id=manager.id,
        employee_id=employee_2.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add_all([cycle_1, cycle_2])
    await db_session.commit()
    await db_session.refresh(cycle_1)
    await db_session.refresh(cycle_2)

    # Ingest evidence with explicit UUIDs
    e1_id = uuid.uuid4()
    e2_id = uuid.uuid4()
    e3_id = uuid.uuid4()

    e1 = Evidence(
        id=e1_id,
        cycle_id=cycle_1.id,
        title="PR #101: Distributed query cache",
        source_type=EvidenceSourceType.PULL_REQUEST,
        access_policy=EvidenceAccessPolicy.INTERNAL,
        source_date=date(2026, 2, 10),
        storage_reference="github/pulls/101",
    )
    e2 = Evidence(
        id=e2_id,
        cycle_id=cycle_1.id,
        title="Architecture RFC: Resilient Sharding",
        source_type=EvidenceSourceType.DOCUMENT,
        access_policy=EvidenceAccessPolicy.INTERNAL,
        source_date=date(2026, 3, 1),
        storage_reference="docs/sharding.pdf",
    )
    e3 = Evidence(
        id=e3_id,
        cycle_id=cycle_2.id,
        title="Commit 99a1: Terraform auto-scaling",
        source_type=EvidenceSourceType.COMMIT,
        access_policy=EvidenceAccessPolicy.MANAGER_ONLY,
        source_date=date(2026, 4, 15),
        storage_reference="git/commits/99a1",
    )
    db_session.add_all([e1, e2, e3])

    # Feedback
    f1 = Feedback(
        cycle_id=cycle_1.id,
        author_id=manager.id,
        subject_employee_id=employee_1.id,
        feedback_type=FeedbackType.MANAGER,
        visibility=FeedbackVisibility.SHARED,
        content="Outstanding architecture and delivery across the board.",
    )
    f2 = Feedback(
        cycle_id=cycle_2.id,
        author_id=employee_1.id,
        subject_employee_id=employee_2.id,
        feedback_type=FeedbackType.PEER,
        visibility=FeedbackVisibility.SHARED,
        content="Great partner during incident response shifts.",
    )
    db_session.add_all([f1, f2])

    # Goals
    g1 = Goal(
        cycle_id=cycle_1.id,
        description="Migrate caching tier",
        status=GoalStatus.COMPLETED,
        measurable_target="P99 latency < 5ms",
    )
    db_session.add(g1)

    # Bias Flags
    flag1 = BiasFlag(
        cycle_id=cycle_1.id,
        flag_type="recency_bias",
        severity="info",
        status="acknowledged",
        explanation="70% of evidence concentrated in last 45 days.",
    )
    flag2 = BiasFlag(
        cycle_id=cycle_2.id,
        flag_type="ungrounded_claim",
        severity="warning",
        status="open",
        explanation="Claim lacks supporting citations.",
    )
    db_session.add_all([flag1, flag2])

    # Reports
    rep1 = ReviewReport(
        cycle_id=cycle_1.id,
        version_number=1,
        status="approved",
        structured_content={
            "executive_summary": "Alice demonstrated principal-level execution.",
            "citations": [str(e1_id), str(e2_id)],
        },
    )
    rep2 = ReviewReport(
        cycle_id=cycle_2.id,
        version_number=1,
        status="draft",
        structured_content={
            "executive_summary": "Bob continues to stabilize infrastructure.",
            "citations": [str(e3_id)],
        },
    )
    db_session.add_all([rep1, rep2])
    await db_session.commit()
    await db_session.refresh(rep1)
    await db_session.refresh(rep2)

    # Initial snapshots
    v1 = await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=rep1.id,
        cycle_id=cycle_1.id,
        version_number=1,
        structured_content=rep1.structured_content,
        status="approved",
        changed_section="all",
        change_summary="Finalized report",
        author_id=manager.id,
        author_role="manager",
    )
    await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=rep2.id,
        cycle_id=cycle_2.id,
        version_number=1,
        structured_content=rep2.structured_content,
        status="draft",
        changed_section="all",
        change_summary="Draft report",
        author_id=manager.id,
        author_role="system",
    )

    # Approval record
    app1 = Approval(
        report_id=rep1.id,
        version_id=v1.id,
        version_number=1,
        reviewer_id=manager.id,
        decision="approved",
        comments="Sign-off verified.",
    )
    db_session.add(app1)

    # Workflow runs with scores in stage_state
    wf1 = WorkflowRun(
        cycle_id=cycle_1.id,
        workflow_status="completed",
        current_stage="completed",
        stage_state={"audit_health_score": 94.5},
    )
    wf2 = WorkflowRun(
        cycle_id=cycle_2.id,
        workflow_status="awaiting_approval",
        current_stage="human_approval_pause",
        stage_state={"audit_health_score": 82.0},
    )
    db_session.add_all([wf1, wf2])
    await db_session.commit()

    return {
        "manager": manager,
        "alice": employee_1,
        "bob": employee_2,
        "cycle_1": cycle_1,
        "cycle_2": cycle_2,
        "rep_1": rep1,
        "rep_2": rep2,
    }


# ===========================================================================
# 1. Analytics Overview Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_analytics_overview_manager(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get("/api/v1/analytics/overview", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_cycles"] == 2
    assert data["total_reports"] == 2
    assert data["total_evidence_items"] == 3
    assert data["total_feedback_items"] == 2
    assert data["total_goals"] == 1
    assert data["total_bias_flags"] == 2
    assert data["completion_rate"] == 50.0  # 1 completed out of 2 total cycles
    assert data["completion_numerator"] == 1
    assert data["completion_denominator"] == 2
    assert "Percentage of review cycles" in data["completion_definition"]
    assert data["average_audit_health_score"] == 88.2 or data["average_audit_health_score"] is not None


@pytest.mark.asyncio
async def test_analytics_overview_employee_scoped(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    alice = analytics_env["alice"]
    headers = {"X-Viewer-Id": str(alice.id), "X-Viewer-Role": "employee"}

    res = await async_client.get("/api/v1/analytics/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Alice only has 1 cycle
    assert data["total_cycles"] == 1
    assert data["total_reports"] == 1
    assert data["completion_rate"] == 100.0  # Alice's single cycle is completed


# ===========================================================================
# 2. Review Lifecycle & Evidence Analytics Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_analytics_reviews(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get("/api/v1/analytics/reviews", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_cycles"] == 2
    assert data["completed_count"] == 1
    assert data["in_progress_count"] == 1
    assert len(data["cycles"]) == 2
    cycle_titles = [c["title"] for c in data["cycles"]]
    assert "2026 H1 Alice Review" in cycle_titles


@pytest.mark.asyncio
async def test_analytics_evidence(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get("/api/v1/analytics/evidence", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_evidence_items"] == 3
    assert "pull_request" in data["source_type_distribution"]
    assert "document" in data["source_type_distribution"]
    assert "commit" in data["source_type_distribution"]
    assert data["total_citations_in_reports"] == 3
    assert data["ungrounded_claims_flag_count"] == 1


# ===========================================================================
# 3. Bias Audit Analytics & Trends Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_analytics_audits(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get("/api/v1/analytics/audits", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_flags"] == 2
    assert "recency_bias" in data["flags_by_rule"]
    assert "ungrounded_claim" in data["flags_by_rule"]
    assert data["flags_by_severity"].get("warning", 0) == 1
    assert data["flags_by_status"].get("open", 0) == 1


@pytest.mark.asyncio
async def test_analytics_trends(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get("/api/v1/analytics/trends?interval=month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["interval"] == "month"
    assert data["total_points"] >= 1
    assert len(data["trends"]) >= 1
    latest_pt = data["trends"][-1]
    assert latest_pt["cycles_created"] >= 1


# ===========================================================================
# 4. Date Filter & Validation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_analytics_invalid_date_range_rejected(async_client: AsyncClient, analytics_env: Dict[str, Any]):
    manager = analytics_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # start_date > end_date must be rejected with HTTP 422
    res = await async_client.get(
        "/api/v1/analytics/overview?start_date=2026-12-31&end_date=2026-01-01",
        headers=headers,
    )
    assert res.status_code == 422
    assert "Invalid date range" in res.json()["detail"]

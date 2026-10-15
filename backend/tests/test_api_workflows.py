import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence, EvidenceAccessPolicy, EvidenceSourceType
from app.models.feedback import Feedback, FeedbackType, FeedbackVisibility
from app.models.goal import Goal, GoalStatus
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.user import User, UserRole


@pytest.fixture
async def workflow_test_env(db_session: AsyncSession):
    manager = User(
        full_name="Team Lead",
        email=f"lead_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    employee = User(
        full_name="Senior SRE",
        email=f"sre_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    unauthorized_employee = User(
        full_name="Unrelated Engineer",
        email=f"unrelated_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([manager, employee, unauthorized_employee])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(employee)
    await db_session.refresh(unauthorized_employee)

    cycle = ReviewCycle(
        title="2026 Mid-Year Engineering Cycle",
        owner_id=manager.id,
        employee_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    other_cycle = ReviewCycle(
        title="Other Employee Cycle",
        owner_id=manager.id,
        employee_id=unauthorized_employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add_all([cycle, other_cycle])
    await db_session.commit()
    await db_session.refresh(cycle)
    await db_session.refresh(other_cycle)

    evidence = Evidence(
        cycle_id=cycle.id,
        source_type=EvidenceSourceType.COMMIT,
        title="Commit abc123: Automated failover orchestrator",
        source_date=date(2026, 3, 15),
        storage_reference="safe/commit_abc123.txt",
        access_policy=EvidenceAccessPolicy.INTERNAL,
    )
    feedback = Feedback(
        cycle_id=cycle.id,
        author_id=manager.id,
        subject_employee_id=employee.id,
        feedback_type=FeedbackType.MANAGER,
        visibility=FeedbackVisibility.SHARED,
        content="Exceptional reliability improvements and on-call leadership.",
    )
    goal = Goal(
        cycle_id=cycle.id,
        description="Reduce MTTR by 40%",
        status=GoalStatus.COMPLETED,
    )
    db_session.add_all([evidence, feedback, goal])
    await db_session.commit()

    return {
        "cycle": cycle,
        "other_cycle": other_cycle,
        "manager": manager,
        "employee": employee,
        "unrelated": unauthorized_employee,
    }


@pytest.mark.asyncio
async def test_start_and_get_workflow_lifecycle(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]

    # 1. Start workflow via manager credentials
    start_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"max_evidence_items": 50},
    )
    assert start_resp.status_code == 201
    start_data = start_resp.json()

    assert start_data["cycle_id"] == str(cycle.id)
    # Graph stops at human approval pause
    assert start_data["workflow_status"] == "awaiting_approval"
    assert start_data["current_stage"] == "human_approval_pause"
    assert len(start_data["stages"]) == 5
    assert start_data["draft_report"] is not None
    assert start_data["draft_report"]["status"] == "draft"
    assert "approve" in start_data["available_actions"]
    assert "request_revision" in start_data["available_actions"]

    run_id = start_data["run_id"]

    # 2. Get workflow status via GET /workflows/{run_id}
    get_resp = await async_client.get(
        f"/api/v1/workflows/{run_id}",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["run_id"] == run_id
    assert get_data["workflow_status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_workflow_start_alias_and_idempotency(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]

    # 1. Start via alias endpoint /workflow-runs
    alias_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflow-runs",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"max_evidence_items": 25},
    )
    assert alias_resp.status_code == 201
    run_id = alias_resp.json()["run_id"]

    # 2. Calling start again with force_re_run=False returns existing active run (idempotency)
    idemp_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"force_re_run": False},
    )
    assert idemp_resp.status_code == 201
    assert idemp_resp.json()["run_id"] == run_id


@pytest.mark.asyncio
async def test_human_approval_and_finalization(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]

    # Start workflow
    start_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    run_id = start_resp.json()["run_id"]

    # Approve workflow
    approve_resp = await async_client.post(
        f"/api/v1/workflows/{run_id}/approve",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"comments": "Excellent contribution. Review finalized and approved."},
    )
    assert approve_resp.status_code == 200
    appr_data = approve_resp.json()
    assert appr_data["workflow_status"] == "completed"
    assert appr_data["current_stage"] == "completed"
    assert appr_data["approval_metadata"]["decision"] == "approved"
    assert "approved" in appr_data["approval_metadata"]["comments"].lower()

    # Attempting to re-approve an already completed workflow raises 409 Conflict
    duplicate_appr = await async_client.post(
        f"/api/v1/workflows/{run_id}/approve",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"comments": "Duplicate approval attempt"},
    )
    assert duplicate_appr.status_code == 409


@pytest.mark.asyncio
async def test_request_revision_lifecycle(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]

    start_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    run_id = start_resp.json()["run_id"]

    # Request revision
    rev_resp = await async_client.post(
        f"/api/v1/workflows/{run_id}/request-revision",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"revision_instructions": "Please add more details regarding the incident postmortem."},
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["workflow_status"] == "revision_requested"
    assert rev_data["current_stage"] == "revision_handling"
    assert rev_data["approval_metadata"]["decision"] == "revision_requested"


@pytest.mark.asyncio
async def test_workflow_authorization_barriers(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]
    employee = workflow_test_env["employee"]
    unrelated = workflow_test_env["unrelated"]

    # Start workflow as manager
    start_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    run_id = start_resp.json()["run_id"]

    # 1. Subject employee can view workflow status and draft report
    emp_view_resp = await async_client.get(
        f"/api/v1/workflows/{run_id}",
        headers={"X-Viewer-Id": str(employee.id), "X-Viewer-Role": "employee"},
    )
    assert emp_view_resp.status_code == 200
    # Employee cannot approve: available_actions is empty
    assert emp_view_resp.json()["available_actions"] == []

    # 2. Subject employee attempting to approve raises 403 Forbidden
    emp_appr_resp = await async_client.post(
        f"/api/v1/workflows/{run_id}/approve",
        headers={"X-Viewer-Id": str(employee.id), "X-Viewer-Role": "employee"},
        json={"comments": "Self-approving my own review"},
    )
    assert emp_appr_resp.status_code == 403

    # 3. Unrelated employee attempting to view raises 403 Forbidden
    unrelated_resp = await async_client.get(
        f"/api/v1/workflows/{run_id}",
        headers={"X-Viewer-Id": str(unrelated.id), "X-Viewer-Role": "employee"},
    )
    assert unrelated_resp.status_code == 403


@pytest.mark.asyncio
async def test_workflow_cancellation(async_client: AsyncClient, workflow_test_env):
    cycle = workflow_test_env["cycle"]
    manager = workflow_test_env["manager"]

    start_resp = await async_client.post(
        f"/api/v1/review-cycles/{cycle.id}/workflows",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    run_id = start_resp.json()["run_id"]

    cancel_resp = await async_client.post(
        f"/api/v1/workflows/{run_id}/cancel",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
        json={"reason": "Review cycle rescheduled"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["workflow_status"] == "cancelled"

    # Subsequent cancellation attempt on cancelled run raises 409
    dup_cancel = await async_client.post(
        f"/api/v1/workflows/{run_id}/cancel",
        headers={"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"},
    )
    assert dup_cancel.status_code == 409

import uuid
from datetime import date
from typing import Any, Dict

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import normalize_role, resolve_principal, verify_manager_or_admin
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.user import User, UserRole
from app.models.workflow_run import WorkflowRun
from app.repositories.report_governance_repository import ReportGovernanceRepository

# ===========================================================================
# 1. Unit Tests for Security Core Functions
# ===========================================================================


def test_normalize_role():
    assert normalize_role("admin") == "admin"
    assert normalize_role("ADMIN") == "admin"
    assert normalize_role(" Manager ") == "manager"
    assert normalize_role("employee") == "employee"
    assert normalize_role("hacker") == "employee"
    assert normalize_role(None) == "employee"
    assert normalize_role(None, default="manager") == "manager"


def test_resolve_principal_header_precedence():
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()

    # Authenticated header MUST override query parameter spoofing
    header_id, header_role = resolve_principal(
        header_id=uid1,
        header_role="employee",
        query_id=uid2,
        query_role="admin",
    )
    assert header_role == "employee"
    assert header_id == uid1

    # Query param accepted only as fallback when header is absent
    fb_id, fb_role = resolve_principal(
        header_id=None,
        header_role=None,
        query_id=uid2,
        query_role="manager",
    )
    assert fb_role == "manager"
    assert fb_id == uid2


def test_verify_manager_or_admin():
    verify_manager_or_admin("manager")
    verify_manager_or_admin("admin")
    with pytest.raises(HTTPException) as exc_info:
        verify_manager_or_admin("employee")
    assert exc_info.value.status_code == 403


# ===========================================================================
# 2. Test Fixture for Security & Isolation Scenarios
# ===========================================================================


@pytest.fixture
async def security_env(db_session: AsyncSession) -> Dict[str, Any]:
    # Manager who oversees Alice
    manager = User(
        full_name="Engineering Director Carol",
        email=f"carol_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    # Alice (Subject Employee)
    alice = User(
        full_name="Senior Engineer Alice",
        email=f"alice_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    # Bob (Unrelated Employee)
    bob = User(
        full_name="Staff Engineer Bob",
        email=f"bob_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    # Manager Dave who is also the subject of their own review cycle
    manager_subject = User(
        full_name="Engineering Manager Dave",
        email=f"dave_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    db_session.add_all([manager, alice, bob, manager_subject])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(alice)
    await db_session.refresh(bob)
    await db_session.refresh(manager_subject)

    # Review cycle for Alice
    alice_cycle = ReviewCycle(
        title="2026 H1 Alice Review",
        owner_id=manager.id,
        employee_id=alice.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    # Review cycle where Dave is both a manager in the org and the subject employee
    dave_cycle = ReviewCycle(
        title="2026 H1 Dave Manager Review",
        owner_id=manager.id,
        employee_id=manager_subject.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add_all([alice_cycle, dave_cycle])
    await db_session.commit()
    await db_session.refresh(alice_cycle)
    await db_session.refresh(dave_cycle)

    # Initial report with sensitive managerial reviewer notes
    initial_content = {
        "executive_summary": "Alice demonstrated outstanding technical leadership in distributed systems.",
        "strengths": [
            {
                "theme": "System Architecture",
                "narrative": "Spearheaded fault-tolerant message queue overhaul.",
                "supporting_evidence_ids": [str(uuid.uuid4())],
                "confidence_score": 0.98,
            }
        ],
        "growth_areas": [
            {
                "theme": "Delegation",
                "narrative": "Empower junior team members on design docs.",
                "supporting_evidence_ids": [str(uuid.uuid4())],
                "confidence_score": 0.85,
            }
        ],
        "reviewer_notes": "CONFIDENTIAL: Planned for promotion to Principal Engineer in Q3 if cross-org impact holds.",
    }

    alice_report = ReviewReport(
        cycle_id=alice_cycle.id,
        status="in_review",
        version_number=1,
        structured_content=initial_content,
    )
    db_session.add(alice_report)
    await db_session.commit()
    await db_session.refresh(alice_report)

    # Initial snapshot v1
    v1 = await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=alice_report.id,
        cycle_id=alice_cycle.id,
        version_number=1,
        structured_content=initial_content,
        status="in_review",
        changed_section="all",
        change_summary="Initial AI review snapshot with confidential manager notes",
        author_id=manager.id,
        author_role="manager",
        is_ai_generated=False,
    )

    # Snapshot v2 with modified notes
    v2_content = dict(initial_content)
    v2_content["executive_summary"] = "Alice demonstrated exceptional leadership and cross-team execution."
    v2_content["reviewer_notes"] = "CONFIDENTIAL: Executive sponsor approved promotion budget."

    v2 = await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=alice_report.id,
        cycle_id=alice_cycle.id,
        version_number=2,
        structured_content=v2_content,
        status="in_review",
        changed_section="executive_summary",
        change_summary="Refined executive summary and updated promotion notes",
        author_id=manager.id,
        author_role="manager",
        is_ai_generated=False,
    )

    # Alice workflow run awaiting approval
    alice_run = WorkflowRun(
        cycle_id=alice_cycle.id,
        workflow_status="awaiting_approval",
        current_stage="human_approval",
        stage_state={
            "employee_id": str(alice.id),
            "current_stage": "human_approval",
            "is_ready_for_review": True,
            "draft_report": initial_content,
        },
    )

    # Dave workflow run awaiting approval (where Dave is the subject)
    dave_run = WorkflowRun(
        cycle_id=dave_cycle.id,
        workflow_status="awaiting_approval",
        current_stage="human_approval",
        stage_state={
            "employee_id": str(manager_subject.id),
            "current_stage": "human_approval",
            "is_ready_for_review": True,
            "draft_report": {"executive_summary": "Draft"},
        },
    )

    # Dave's report for self-approval testing
    dave_report = ReviewReport(
        cycle_id=dave_cycle.id,
        status="in_review",
        version_number=1,
        structured_content={"executive_summary": "Dave managed engineering team operations effectively."},
    )
    db_session.add_all([alice_run, dave_run, dave_report])
    await db_session.commit()
    await db_session.refresh(alice_run)
    await db_session.refresh(dave_run)
    await db_session.refresh(dave_report)

    return {
        "manager": manager,
        "alice": alice,
        "bob": bob,
        "manager_subject": manager_subject,
        "alice_cycle": alice_cycle,
        "dave_cycle": dave_cycle,
        "alice_report": alice_report,
        "dave_report": dave_report,
        "alice_run": alice_run,
        "dave_run": dave_run,
        "v1": v1,
        "v2": v2,
    }


# ===========================================================================
# 3. Query Parameter Privilege Escalation Defenses
# ===========================================================================


@pytest.mark.asyncio
async def test_query_param_spoofing_prevented_in_analytics(async_client: AsyncClient, security_env: Dict[str, Any]):
    """
    An employee trying to escalate to admin privileges via ?viewer_role=admin
    must be ignored when X-Viewer-Role header is 'employee'.
    """
    alice = security_env["alice"]

    headers = {
        "X-Viewer-Id": str(alice.id),
        "X-Viewer-Role": "employee",
    }
    # Attempting to fetch admin analytics using query parameter
    res = await async_client.get(
        f"/api/v1/analytics/overview?viewer_role=admin&viewer_id={alice.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    # The response MUST be scoped to employee role (only Alice's 1 cycle), not global admin (2 cycles)
    assert data["total_cycles"] == 1
    assert data["total_reports"] == 1


@pytest.mark.asyncio
async def test_query_param_spoofing_prevented_in_workflow_approval(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    An employee passing ?viewer_role=admin or ?viewer_role=manager to approve
    a review cycle workflow MUST be rejected with HTTP 403.
    """
    alice = security_env["alice"]
    alice_run = security_env["alice_run"]

    headers = {
        "X-Viewer-Id": str(alice.id),
        "X-Viewer-Role": "employee",
    }
    res = await async_client.post(
        f"/api/v1/workflows/{alice_run.id}/approve?viewer_role=admin&reviewer_id={alice.id}",
        headers=headers,
        json={"notes": "Attempted self-approval via spoofed query parameter"},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_query_param_spoofing_prevented_in_report_approval(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    An employee attempting to approve a report via query parameter spoofing
    MUST be rejected with HTTP 403.
    """
    alice = security_env["alice"]
    alice_report = security_env["alice_report"]

    headers = {
        "X-Viewer-Id": str(alice.id),
        "X-Viewer-Role": "employee",
    }
    res = await async_client.post(
        f"/api/v1/reports/{alice_report.id}/approve?viewer_role=manager&reviewer_id={alice.id}",
        headers=headers,
        json={"notes": "Spoofed manager approval"},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


# ===========================================================================
# 4. Anonymous / Missing Identity Denials
# ===========================================================================


@pytest.mark.asyncio
async def test_employee_request_without_viewer_id_is_denied(async_client: AsyncClient, security_env: Dict[str, Any]):
    """
    Employee requests without X-Viewer-Id or viewer_id cannot be authorized
    to view reports or exports.
    """
    alice_report = security_env["alice_report"]

    headers = {
        "X-Viewer-Role": "employee",
        # Intentionally missing X-Viewer-Id
    }
    # Report detail
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}", headers=headers)
    assert res.status_code == 404

    # Version snapshot
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/1", headers=headers)
    assert res.status_code == 404

    # Export
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/export/pdf", headers=headers)
    assert res.status_code == 404


# ===========================================================================
# 5. Cross-Employee Isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_cross_employee_cannot_access_other_employee_report(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    Bob cannot view, compare, list versions, or export Alice's performance report.
    """
    bob = security_env["bob"]
    alice_report = security_env["alice_report"]
    alice_cycle = security_env["alice_cycle"]

    headers = {
        "X-Viewer-Id": str(bob.id),
        "X-Viewer-Role": "employee",
    }

    # 1. Report Detail
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}", headers=headers)
    assert res.status_code == 404

    # 2. Cycle-level Report
    res = await async_client.get(f"/api/v1/review-cycles/{alice_cycle.id}/report", headers=headers)
    assert res.status_code == 404

    # 3. Version Listing
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions", headers=headers)
    assert res.status_code == 404

    # 4. Version Snapshot
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/1", headers=headers)
    assert res.status_code == 404

    # 5. Version Comparison
    res = await async_client.get(
        f"/api/v1/reports/{alice_report.id}/compare?from_version=1&to_version=2", headers=headers
    )
    assert res.status_code == 404

    # 6. PDF Export
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/export/pdf", headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cross_employee_cannot_access_other_employee_workflow_state(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    Bob cannot inspect Alice's cycle workflows or workflow run execution status.
    """
    bob = security_env["bob"]
    alice_cycle = security_env["alice_cycle"]
    alice_run = security_env["alice_run"]

    headers = {
        "X-Viewer-Id": str(bob.id),
        "X-Viewer-Role": "employee",
    }
    # List cycle workflows
    res = await async_client.get(f"/api/v1/review-cycles/{alice_cycle.id}/workflows", headers=headers)
    assert res.status_code == 403

    # Get specific workflow run details
    res = await async_client.get(f"/api/v1/workflows/{alice_run.id}", headers=headers)
    assert res.status_code == 403


# ===========================================================================
# 6. Sensitive Reviewer Notes Masking for Employees
# ===========================================================================


@pytest.mark.asyncio
async def test_reviewer_notes_masked_in_report_detail_and_snapshots_for_employee(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    Confidential reviewer_notes must be visible to manager/admin but completely
    masked or stripped when retrieved by the employee.
    """
    manager = security_env["manager"]
    alice = security_env["alice"]
    alice_report = security_env["alice_report"]

    mgr_headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}
    emp_headers = {"X-Viewer-Id": str(alice.id), "X-Viewer-Role": "employee"}

    # --- 1. Current Report Detail ---
    # Manager sees reviewer_notes
    mgr_res = await async_client.get(f"/api/v1/reports/{alice_report.id}", headers=mgr_headers)
    assert mgr_res.status_code == 200
    assert "reviewer_notes" in mgr_res.json()["structured_content"]
    assert "Principal Engineer" in mgr_res.json()["structured_content"]["reviewer_notes"]

    # Employee does NOT see reviewer_notes
    emp_res = await async_client.get(f"/api/v1/reports/{alice_report.id}", headers=emp_headers)
    assert emp_res.status_code == 200
    emp_content = emp_res.json()["structured_content"]
    assert emp_content.get("reviewer_notes") is None

    # --- 2. Historical Version Snapshot ---
    # Manager sees reviewer_notes in snapshot
    mgr_v1 = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/1", headers=mgr_headers)
    assert mgr_v1.status_code == 200
    assert "reviewer_notes" in mgr_v1.json()["structured_content"]

    # Employee does NOT see reviewer_notes in snapshot
    emp_v1 = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/1", headers=emp_headers)
    assert emp_v1.status_code == 200
    assert emp_v1.json()["structured_content"].get("reviewer_notes") is None

    # --- 3. Version Comparison Diffs ---
    # Manager sees reviewer_notes comparison
    mgr_cmp = await async_client.get(
        f"/api/v1/reports/{alice_report.id}/compare?from_version=1&to_version=2", headers=mgr_headers
    )
    assert mgr_cmp.status_code == 200
    mgr_cmp_data = mgr_cmp.json()
    assert "reviewer_notes" in mgr_cmp_data["section_diffs"]

    # Employee comparison diffs MUST NOT expose confidential reviewer_notes
    emp_cmp = await async_client.get(
        f"/api/v1/reports/{alice_report.id}/compare?from_version=1&to_version=2", headers=emp_headers
    )
    assert emp_cmp.status_code == 200
    emp_cmp_data = emp_cmp.json()
    assert "reviewer_notes" not in emp_cmp_data["section_diffs"]
    for summary_line in emp_cmp_data["change_summary"]:
        assert "Principal Engineer" not in summary_line
        assert "promotion" not in summary_line.lower()


# ===========================================================================
# 7. Manager Self-Approval Prevention
# ===========================================================================


@pytest.mark.asyncio
async def test_manager_cannot_approve_own_review_cycle_or_report(
    async_client: AsyncClient, security_env: Dict[str, Any]
):
    """
    Even if a user holds a MANAGER role in the system, they cannot approve
    their own performance review cycle or report when they are the subject.
    """
    dave = security_env["manager_subject"]
    dave_run = security_env["dave_run"]
    dave_report = security_env["dave_report"]

    dave_headers = {
        "X-Viewer-Id": str(dave.id),
        "X-Viewer-Role": "manager",
    }

    # 1. Workflow approval attempt
    wf_res = await async_client.post(
        f"/api/v1/workflows/{dave_run.id}/approve",
        headers=dave_headers,
        json={"notes": "Attempting to approve my own review"},
    )
    assert wf_res.status_code == 403
    assert "cannot approve" in wf_res.json()["detail"].lower()

    # 2. Report governance approval attempt
    rep_res = await async_client.post(
        f"/api/v1/reports/{dave_report.id}/approve",
        headers=dave_headers,
        json={"notes": "Attempting to approve my own report"},
    )
    assert rep_res.status_code == 403
    assert "cannot approve" in rep_res.json()["detail"].lower()

    # 3. Report governance revision request attempt
    rev_res = await async_client.post(
        f"/api/v1/reports/{dave_report.id}/request-revision",
        headers=dave_headers,
        json={"comments": "Attempting to request revision on my own report"},
    )
    assert rev_res.status_code == 403
    assert "their own" in rev_res.json()["detail"].lower()


# ===========================================================================
# 8. Out-of-Bounds and Invalid Input Parameter Validation
# ===========================================================================


@pytest.mark.asyncio
async def test_out_of_bounds_version_numbers_rejected(async_client: AsyncClient, security_env: Dict[str, Any]):
    """
    Non-positive version numbers (0, negative integers) must be rejected with HTTP 422.
    """
    manager = security_env["manager"]
    alice_report = security_env["alice_report"]

    headers = {
        "X-Viewer-Id": str(manager.id),
        "X-Viewer-Role": "manager",
    }

    # Snapshot with version 0
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/0", headers=headers)
    assert res.status_code == 422

    # Snapshot with version -1
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/versions/-1", headers=headers)
    assert res.status_code == 422

    # Compare with from_version=0
    res = await async_client.get(
        f"/api/v1/reports/{alice_report.id}/compare?from_version=0&to_version=1", headers=headers
    )
    assert res.status_code == 422

    # Compare with negative version
    res = await async_client.get(
        f"/api/v1/reports/{alice_report.id}/compare?from_version=1&to_version=-2", headers=headers
    )
    assert res.status_code == 422

    # Export with version_number 0
    res = await async_client.get(f"/api/v1/reports/{alice_report.id}/export/pdf?version_number=0", headers=headers)
    assert res.status_code == 422

    # Section edit with base_version_number = 0
    res = await async_client.post(
        f"/api/v1/reports/{alice_report.id}/sections/executive_summary",
        headers=headers,
        json={
            "content": "Updated content",
            "base_version_number": 0,
        },
    )
    assert res.status_code == 422

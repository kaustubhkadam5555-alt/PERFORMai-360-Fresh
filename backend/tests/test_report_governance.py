import uuid
from datetime import date
from typing import Any, Dict

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.user import User, UserRole
from app.repositories.report_governance_repository import ReportGovernanceRepository


@pytest.fixture
async def governance_env(db_session: AsyncSession) -> Dict[str, Any]:
    manager = User(
        full_name="Staff Engineering Manager",
        email=f"em_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    employee = User(
        full_name="Senior Distributed Systems Engineer",
        email=f"engineer_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    other_employee = User(
        full_name="Unrelated Employee",
        email=f"unrelated_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([manager, employee, other_employee])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(employee)
    await db_session.refresh(other_employee)

    cycle = ReviewCycle(
        title="2026 H1 Engineering Review",
        owner_id=manager.id,
        employee_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    initial_content = {
        "executive_summary": "Demonstrated solid technical execution on the distributed cache project.",
        "strengths": [
            {
                "theme": "Distributed Systems",
                "narrative": "Led caching migration with zero downtime.",
                "supporting_evidence_ids": [str(uuid.uuid4())],
                "confidence_score": 0.95,
            }
        ],
        "growth_areas": [
            {
                "theme": "Cross-functional Communication",
                "narrative": "Provide more proactive updates to product stakeholders.",
                "supporting_evidence_ids": [str(uuid.uuid4())],
                "confidence_score": 0.88,
            }
        ],
        "citations": [],
    }

    report = ReviewReport(
        cycle_id=cycle.id,
        status="draft",
        version_number=1,
        structured_content=initial_content,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    # Initial snapshot
    v1 = await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=report.id,
        cycle_id=cycle.id,
        version_number=1,
        structured_content=initial_content,
        status="draft",
        changed_section="all",
        change_summary="Initial AI-generated draft snapshot",
        author_id=manager.id,
        author_role="system",
        is_ai_generated=True,
    )

    return {
        "manager": manager,
        "employee": employee,
        "other_employee": other_employee,
        "cycle": cycle,
        "report": report,
        "initial_version": v1,
    }


# ===========================================================================
# 1. Section-Level Editing & Optimistic Concurrency Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_edit_report_section_success(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {
        "X-Viewer-Id": str(manager.id),
        "X-Viewer-Role": "manager",
    }
    payload = {
        "content": "Updated executive summary highlighting major cross-datacenter cache achievements.",
        "reason": "Clarified cross-datacenter scope after architectural review",
        "base_version_number": 1,
    }

    res = await async_client.post(
        f"/api/v1/reports/{report.id}/sections/executive_summary",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["version_number"] == 2
    assert data["status"] == "draft"
    assert "cross-datacenter" in data["structured_content"]["executive_summary"]

    # Verify version listing now shows 2 versions
    v_res = await async_client.get(f"/api/v1/reports/{report.id}/versions", headers=headers)
    assert v_res.status_code == 200
    versions_data = v_res.json()
    assert versions_data["total_versions"] == 2
    assert versions_data["versions"][0]["version_number"] == 2
    assert versions_data["versions"][0]["changed_section"] == "executive_summary"
    assert versions_data["versions"][0]["is_ai_generated"] is False


@pytest.mark.asyncio
async def test_edit_section_optimistic_concurrency_conflict(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # First edit advances version 1 -> 2
    first_res = await async_client.post(
        f"/api/v1/reports/{report.id}/sections/executive_summary",
        json={
            "content": "First update content.",
            "reason": "First manager edit",
            "base_version_number": 1,
        },
        headers=headers,
    )
    assert first_res.status_code == 200

    # Second edit based on stale version 1 must be rejected with HTTP 409
    stale_res = await async_client.post(
        f"/api/v1/reports/{report.id}/sections/executive_summary",
        json={
            "content": "Stale update content that should conflict.",
            "reason": "Concurrent edit based on stale version",
            "base_version_number": 1,
        },
        headers=headers,
    )
    assert stale_res.status_code == 409
    assert "Version conflict" in stale_res.json()["detail"]


@pytest.mark.asyncio
async def test_edit_unsupported_section_rejected(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}
    res = await async_client.post(
        f"/api/v1/reports/{report.id}/sections/arbitrary_malformed_key",
        json={
            "content": "Malformed section content",
            "reason": "Test",
            "base_version_number": 1,
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert "Invalid section" in res.json()["detail"]


# ===========================================================================
# 2. Immutable Report Version History & Snapshot Retrieval Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_get_version_by_number_and_uuid(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]
    v1 = governance_env["initial_version"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # Fetch by version number
    res_num = await async_client.get(f"/api/v1/reports/{report.id}/versions/1", headers=headers)
    assert res_num.status_code == 200
    assert res_num.json()["version_number"] == 1
    assert res_num.json()["is_ai_generated"] is True

    # Fetch by version UUID
    res_uuid = await async_client.get(f"/api/v1/reports/{report.id}/versions/{v1.id}", headers=headers)
    assert res_uuid.status_code == 200
    assert res_uuid.json()["version_id"] == str(v1.id)
    assert res_uuid.json()["version_number"] == 1


# ===========================================================================
# 3. Deterministic Version Comparison Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_compare_versions_deterministic_diff(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # Create version 2 with updated summary
    await async_client.post(
        f"/api/v1/reports/{report.id}/sections/executive_summary",
        json={
            "content": "Expanded executive summary with quantitative metrics and impact numbers.",
            "reason": "Added metrics",
            "base_version_number": 1,
        },
        headers=headers,
    )

    # Compare version 1 to 2
    comp_res = await async_client.get(
        f"/api/v1/reports/{report.id}/compare?from_version=1&to_version=2",
        headers=headers,
    )
    assert comp_res.status_code == 200, comp_res.text
    diff_data = comp_res.json()

    assert diff_data["from_version_number"] == 1
    assert diff_data["to_version_number"] == 2
    assert "executive_summary" in diff_data["sections_changed"]
    assert "executive_summary" in diff_data["section_diffs"]
    assert diff_data["section_diffs"]["executive_summary"]["diff_type"] == "text"
    assert "Expanded executive summary" in diff_data["section_diffs"]["executive_summary"]["unified_diff"]


# ===========================================================================
# 4. Human Approval & Protected Approved Version Invariance Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_approve_report_and_stale_approval_protection(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # Stale approval defense: if manager requests approval for version 999
    stale_app_res = await async_client.post(
        f"/api/v1/reports/{report.id}/approve",
        json={"version_number": 999, "comments": "Approval with bad version"},
        headers=headers,
    )
    assert stale_app_res.status_code == 409
    assert "Stale approval rejected" in stale_app_res.json()["detail"]

    # Legitimate approval for version 1
    app_res = await async_client.post(
        f"/api/v1/reports/{report.id}/approve",
        json={"version_number": 1, "comments": "Fully vetted and approved for H1 review."},
        headers=headers,
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["status"] == "approved"
    assert app_data["version_number"] == 1

    # Historical snapshot v1 must remain 'approved'
    v1_res = await async_client.get(f"/api/v1/reports/{report.id}/versions/1", headers=headers)
    assert v1_res.json()["status"] == "approved"

    # Idempotency / duplicate approval defense: approving again returns 409
    dup_res = await async_client.post(
        f"/api/v1/reports/{report.id}/approve",
        json={"version_number": 1, "comments": "Second approval attempt"},
        headers=headers,
    )
    assert dup_res.status_code == 409


@pytest.mark.asyncio
async def test_approved_version_invariance_on_subsequent_edit(
    async_client: AsyncClient, governance_env: Dict[str, Any]
):
    """
    Critical PRD & Architecture Requirement:
    Editing an approved report creates a new version in draft status,
    while the historical approved version snapshot remains frozen and unchanged.
    """
    report = governance_env["report"]
    manager = governance_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # 1. Approve version 1
    await async_client.post(
        f"/api/v1/reports/{report.id}/approve",
        json={"version_number": 1, "comments": "Original sign-off"},
        headers=headers,
    )

    # 2. Subsequent edit by manager creates version 2
    edit_res = await async_client.post(
        f"/api/v1/reports/{report.id}/sections/reviewer_notes",
        json={
            "content": "Additional manager feedback added after post-review check-in.",
            "reason": "Post-review notes",
            "base_version_number": 1,
        },
        headers=headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["version_number"] == 2
    assert edit_res.json()["status"] == "draft"

    # 3. Verify that version 1 is still preserved as 'approved'
    v1_check = await async_client.get(f"/api/v1/reports/{report.id}/versions/1", headers=headers)
    assert v1_check.json()["status"] == "approved"

    # 4. Verify version 2 is 'draft' and did NOT inherit the approval
    v2_check = await async_client.get(f"/api/v1/reports/{report.id}/versions/2", headers=headers)
    assert v2_check.json()["status"] == "draft"


# ===========================================================================
# 5. Revision Request Lifecycle Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_request_revision_lifecycle(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]
    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    rev_res = await async_client.post(
        f"/api/v1/reports/{report.id}/request-revision",
        json={"comments": "Please incorporate code review metrics and CI/CD contributions."},
        headers=headers,
    )
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["status"] == "revision_requested"

    # Verify approval history records this request
    app_hist_res = await async_client.get(f"/api/v1/reports/{report.id}/approvals", headers=headers)
    assert app_hist_res.status_code == 200
    approvals = app_hist_res.json()["approvals"]
    assert len(approvals) >= 1
    assert approvals[0]["decision"] == "revision_requested"
    assert "code review metrics" in approvals[0]["comments"]


# ===========================================================================
# 6. Authorization & Scoping Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_employee_cannot_approve_own_review(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    employee = governance_env["employee"]

    # Employee attempting to approve their own report is forbidden
    res = await async_client.post(
        f"/api/v1/reports/{report.id}/approve",
        json={"version_number": 1, "comments": "Self-approval attempt"},
        headers={"X-Viewer-Id": str(employee.id), "X-Viewer-Role": "employee"},
    )
    assert res.status_code in {403, 404}


@pytest.mark.asyncio
async def test_unrelated_employee_access_blocked(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    other_employee = governance_env["other_employee"]

    # Unrelated employee cannot view the report
    res = await async_client.get(
        f"/api/v1/reports/{report.id}",
        headers={"X-Viewer-Id": str(other_employee.id), "X-Viewer-Role": "employee"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_audit_events_endpoint(async_client: AsyncClient, governance_env: Dict[str, Any]):
    report = governance_env["report"]
    manager = governance_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # Perform an edit to trigger an audit event
    await async_client.post(
        f"/api/v1/reports/{report.id}/sections/executive_summary",
        json={
            "content": "Audit-logged edit content.",
            "reason": "Security and governance verification",
            "base_version_number": 1,
        },
        headers=headers,
    )

    audit_res = await async_client.get(f"/api/v1/reports/{report.id}/audit-events", headers=headers)
    assert audit_res.status_code == 200
    events = audit_res.json()["events"]
    assert len(events) >= 1
    actions = [e["action"] for e in events]
    assert "report.section_edited" in actions

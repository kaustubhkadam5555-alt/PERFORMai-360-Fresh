import uuid
from datetime import date
from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_audit_environment(async_client: AsyncClient) -> Dict[str, Any]:
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"audit_emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dev Edward", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={
            "email": f"audit_mgr_{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Manager Monica",
            "role": "manager",
        },
    )
    owner_id = mgr_res.json()["id"]

    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Edward H1 Performance Review",
            "employee_id": employee_id,
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    cycle_id = cycle_res.json()["id"]

    # Transition cycle to active status to permit feedback submissions
    await async_client.patch(
        f"/api/v1/review-cycles/{cycle_id}",
        json={"status": "active"},
    )

    # Register sample evidence in recent window (potential recency concentration)
    today = date(2026, 6, 25)
    ev_res = await async_client.post(
        "/api/v1/evidence",
        json={
            "cycle_id": cycle_id,
            "title": "PR #550: Async Task Queue Implementation",
            "source_type": "pull_request",
            "source_date": today.isoformat(),
            "storage_reference": "github/pulls/550",
            "metadata_json": {"snippet": "Implemented Celery-based worker queue."},
            "access_policy": "internal",
        },
    )
    evidence_id = ev_res.json()["id"]

    # Register manager feedback with vague language
    fb_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "cycle_id": cycle_id,
            "author_id": owner_id,
            "subject_employee_id": employee_id,
            "feedback_type": "manager",
            "content": "Edward always completes deliverables on time.",
            "visibility": "shared",
        },
    )
    feedback_id = fb_res.json()["id"]

    return {
        "employee_id": employee_id,
        "owner_id": owner_id,
        "cycle_id": cycle_id,
        "evidence_id": evidence_id,
        "feedback_id": feedback_id,
    }


@pytest.mark.asyncio
async def test_run_audit_endpoint(async_client: AsyncClient, setup_audit_environment):
    env = setup_audit_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    # 1. Execute audit
    response = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/audit",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["cycle_id"] == cycle_id
    assert data["total_flags"] > 0
    assert data["open_flags"] > 0
    assert 0.0 <= data["audit_health_score"] <= 1.0
    assert "severity_breakdown" in data
    assert "flag_type_breakdown" in data

    # Verify vague language flag detected "always"
    flag_types = [f["flag_type"] for f in data["flags"]]
    assert "vague_or_absolute_claims" in flag_types

    # 2. Test alias endpoint (/bias-audit)
    alias_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/bias-audit",
        headers=headers,
    )
    assert alias_res.status_code == 200
    assert alias_res.json()["total_flags"] == data["total_flags"]


@pytest.mark.asyncio
async def test_list_audit_flags_and_summary(async_client: AsyncClient, setup_audit_environment):
    env = setup_audit_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    # Execute audit first
    await async_client.post(f"/api/v1/review-cycles/{cycle_id}/audit", headers=headers)

    # 1. List flags
    flags_res = await async_client.get(f"/api/v1/review-cycles/{cycle_id}/audit-flags", headers=headers)
    assert flags_res.status_code == 200
    flags = flags_res.json()
    assert len(flags) > 0

    # 2. Filter by status
    open_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/audit-flags?status=open",
        headers=headers,
    )
    assert open_res.status_code == 200
    assert all(f["status"] == "open" for f in open_res.json())

    # 3. Get audit summary
    summary_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/audit-summary",
        headers=headers,
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_flags"] == len(flags)


@pytest.mark.asyncio
async def test_update_audit_flag_status_and_health_recalculation(async_client: AsyncClient, setup_audit_environment):
    env = setup_audit_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    # Execute audit
    audit_res = await async_client.post(f"/api/v1/review-cycles/{cycle_id}/audit", headers=headers)
    initial_score = audit_res.json()["audit_health_score"]
    flag_id = audit_res.json()["flags"][0]["id"]

    # Manager acknowledges the flag with calibration notes
    update_res = await async_client.patch(
        f"/api/v1/review-cycles/{cycle_id}/audit-flags/{flag_id}",
        json={
            "status": "acknowledged",
            "reviewer_comment": "Calibrated with committee; verified work is consistent across sprints.",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["status"] == "acknowledged"
    assert "Calibrated with committee" in updated_data["reviewer_comment"]

    # Verify score improves after acknowledgment
    summary_res = await async_client.get(f"/api/v1/review-cycles/{cycle_id}/audit-summary", headers=headers)
    new_score = summary_res.json()["audit_health_score"]
    assert new_score >= initial_score


@pytest.mark.asyncio
async def test_cross_cycle_flag_isolation(async_client: AsyncClient, setup_audit_environment):
    env = setup_audit_environment
    cycle_1_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    # Create cycle 2
    c2_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Unrelated Review Cycle",
            "employee_id": env["employee_id"],
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    cycle_2_id = c2_res.json()["id"]

    # Audit Cycle 1
    audit_res = await async_client.post(f"/api/v1/review-cycles/{cycle_1_id}/audit", headers=headers)
    flag_1_id = audit_res.json()["flags"][0]["id"]

    # Attempt to update Cycle 1's flag via Cycle 2's route
    leak_res = await async_client.patch(
        f"/api/v1/review-cycles/{cycle_2_id}/audit-flags/{flag_1_id}",
        json={"status": "resolved"},
        headers=headers,
    )
    assert leak_res.status_code == 404
    assert "does not belong" in leak_res.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_mutate_flag(async_client: AsyncClient, setup_audit_environment):
    env = setup_audit_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    emp_id = env["employee_id"]

    # Manager runs audit
    audit_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/audit",
        headers={"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"},
    )
    flag_id = audit_res.json()["flags"][0]["id"]

    # Employee tries to resolve their own audit flag
    forbidden_res = await async_client.patch(
        f"/api/v1/review-cycles/{cycle_id}/audit-flags/{flag_id}",
        json={"status": "resolved"},
        headers={"X-Viewer-Id": emp_id, "X-Viewer-Role": "employee"},
    )
    assert forbidden_res.status_code == 403
    assert "Only managers" in forbidden_res.json()["detail"]

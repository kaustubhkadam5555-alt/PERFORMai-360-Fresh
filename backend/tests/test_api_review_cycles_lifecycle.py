import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_review_cycle_valid_lifecycle_transitions(async_client: AsyncClient):
    # Setup employee and manager
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Reviewee Bob", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Alice", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    today = date.today()
    payload = {
        "title": "H1 2026 Engineering Cycle",
        "employee_id": employee_id,
        "owner_id": owner_id,
        "period_start": (today - timedelta(days=90)).isoformat(),
        "period_end": today.isoformat(),
        "template_id": "standard_swe_v1",
    }

    # 1. Create cycle -> initial state is draft
    res = await async_client.post("/api/v1/review-cycles", json=payload)
    assert res.status_code == 201
    cycle = res.json()
    cycle_id = cycle["id"]
    assert cycle["status"] == "draft"

    # 2. draft -> active
    patch_res = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "active"

    # 3. active -> in_review
    patch_res = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "in_review"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_review"

    # 4. in_review -> completed
    patch_res = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "completed"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"

    # 5. completed -> archived
    patch_res = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "archived"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_review_cycle_invalid_lifecycle_transitions(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Reviewee Bob", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Alice", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    today = date.today()
    payload = {
        "title": "H1 2026 Cycle Invalid Transitions",
        "employee_id": employee_id,
        "owner_id": owner_id,
        "period_start": (today - timedelta(days=90)).isoformat(),
        "period_end": today.isoformat(),
        "template_id": "standard_swe_v1",
    }

    res = await async_client.post("/api/v1/review-cycles", json=payload)
    cycle_id = res.json()["id"]

    # Invalid: draft cannot transition directly to completed
    bad_patch = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "completed"})
    assert bad_patch.status_code == 409
    assert "Invalid review cycle status transition" in bad_patch.json()["detail"]

    # Transition to active
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})

    # Transition to in_review then completed
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "in_review"})
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "completed"})

    # Invalid: completed cannot transition back to draft
    bad_patch2 = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "draft"})
    assert bad_patch2.status_code == 409

    # Transition to archived (terminal)
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "archived"})

    # Invalid: archived cannot transition to active
    bad_patch3 = await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})
    assert bad_patch3.status_code == 409


@pytest.mark.asyncio
async def test_review_cycle_period_validation_on_update(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Reviewee Bob", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Alice", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    payload = {
        "title": "Period Test Cycle",
        "employee_id": employee_id,
        "owner_id": owner_id,
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
    }
    create_res = await async_client.post("/api/v1/review-cycles", json=payload)
    cycle_id = create_res.json()["id"]

    # Invalid: period_end before period_start
    bad_patch = await async_client.patch(
        f"/api/v1/review-cycles/{cycle_id}",
        json={"period_end": "2025-12-31"},
    )
    assert bad_patch.status_code == 422


@pytest.mark.asyncio
async def test_review_cycle_delete_rules(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Reviewee Bob", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Alice", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    payload = {
        "title": "Draft Cycle For Deletion",
        "employee_id": employee_id,
        "owner_id": owner_id,
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
    }
    res = await async_client.post("/api/v1/review-cycles", json=payload)
    cycle_id = res.json()["id"]

    # Delete draft cycle succeeds
    del_res = await async_client.delete(f"/api/v1/review-cycles/{cycle_id}")
    assert del_res.status_code == 204

    # Verify 404 on get
    get_res = await async_client.get(f"/api/v1/review-cycles/{cycle_id}")
    assert get_res.status_code == 404

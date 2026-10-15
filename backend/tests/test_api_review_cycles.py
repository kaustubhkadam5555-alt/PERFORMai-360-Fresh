import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_update_review_cycle(async_client: AsyncClient):
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
        "title": "H2 2026 Engineering Review",
        "employee_id": employee_id,
        "owner_id": owner_id,
        "period_start": (today - timedelta(days=90)).isoformat(),
        "period_end": today.isoformat(),
        "template_id": "standard_swe_v1",
    }

    create_res = await async_client.post("/api/v1/review-cycles", json=payload)
    assert create_res.status_code == 201
    cycle = create_res.json()
    assert cycle["title"] == "H2 2026 Engineering Review"
    assert cycle["status"] == "draft"
    assert "id" in cycle

    cycle_id = cycle["id"]

    # Patch status to open
    patch_res = await async_client.patch(
        f"/api/v1/review-cycles/{cycle_id}",
        json={"status": "open", "title": "Updated Title H2 2026"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "open"
    assert updated["title"] == "Updated Title H2 2026"

    # Get by ID
    get_res = await async_client.get(f"/api/v1/review-cycles/{cycle_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == cycle_id


@pytest.mark.asyncio
async def test_review_cycle_invalid_period(async_client: AsyncClient):
    today = date.today()
    payload = {
        "title": "Invalid Review Period",
        "employee_id": str(uuid.uuid4()),
        "owner_id": str(uuid.uuid4()),
        "period_start": today.isoformat(),
        "period_end": (today - timedelta(days=10)).isoformat(),  # Invalid: end before start
    }
    response = await async_client.post("/api/v1/review-cycles", json=payload)
    assert response.status_code == 422
    assert "period_end must be on or after period_start" in response.text

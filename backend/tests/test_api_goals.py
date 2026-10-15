import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_goal_environment(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dev Dana", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Mike", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Dana 2026 Goals Cycle",
            "employee_id": employee_id,
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    cycle_id = cycle_res.json()["id"]

    return {
        "employee_id": employee_id,
        "owner_id": owner_id,
        "cycle_id": cycle_id,
    }


@pytest.mark.asyncio
async def test_create_and_manage_goals(async_client: AsyncClient, setup_goal_environment):
    env = setup_goal_environment
    cycle_id = env["cycle_id"]
    employee_id = env["employee_id"]

    # 1. Create a goal via nested endpoint
    goal_payload = {
        "description": "Deliver payment service v2 migration",
        "measurable_target": "99.99% uptime with p99 latency under 80ms",
        "status": "in_progress",
        "due_date": "2026-09-30",
    }
    create_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/goals",
        json=goal_payload,
    )
    assert create_res.status_code == 201
    goal = create_res.json()
    assert goal["description"] == "Deliver payment service v2 migration"
    assert goal["status"] == "in_progress"
    goal_id = goal["id"]

    # 2. Retrieve goal by ID
    get_res = await async_client.get(f"/api/v1/goals/{goal_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == goal_id

    # 3. List goals by cycle
    list_res = await async_client.get(f"/api/v1/review-cycles/{cycle_id}/goals")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert any(g["id"] == goal_id for g in list_res.json())

    # 4. List goals by employee
    list_emp = await async_client.get("/api/v1/goals", params={"employee_id": employee_id})
    assert list_emp.status_code == 200
    assert any(g["id"] == goal_id for g in list_emp.json())

    # 5. Update goal with outcome notes and completed status
    patch_res = await async_client.patch(
        f"/api/v1/goals/{goal_id}",
        json={
            "status": "completed",
            "outcome_notes": "Successfully migrated payment service; exceeded latency SLA with p99 of 65ms.",
        },
    )
    assert patch_res.status_code == 200
    updated_goal = patch_res.json()
    assert updated_goal["status"] == "completed"
    assert "Successfully migrated" in updated_goal["outcome_notes"]

    # 6. Delete goal
    del_res = await async_client.delete(f"/api/v1/goals/{goal_id}")
    assert del_res.status_code == 204

    # 7. Verify deletion
    verify_res = await async_client.get(f"/api/v1/goals/{goal_id}")
    assert verify_res.status_code == 404


@pytest.mark.asyncio
async def test_goal_validation_rules(async_client: AsyncClient, setup_goal_environment):
    env = setup_goal_environment
    cycle_id = env["cycle_id"]

    # Invalid status value
    bad_status = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/goals",
        json={
            "description": "Invalid goal status",
            "status": "super_completed",
        },
    )
    assert bad_status.status_code == 422

    # Mismatched employee ID
    random_user_id = str(uuid.uuid4())
    mismatched = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/goals",
        json={
            "description": "Goal for different employee",
            "employee_id": random_user_id,
        },
    )
    assert mismatched.status_code in (404, 422)

    # Missing non-existent cycle
    bad_cycle = str(uuid.uuid4())
    missing_res = await async_client.post(
        f"/api/v1/review-cycles/{bad_cycle}/goals",
        json={"description": "Missing cycle goal"},
    )
    assert missing_res.status_code == 404

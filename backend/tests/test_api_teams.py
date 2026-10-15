import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_team(async_client: AsyncClient):
    mgr_email = f"lead_{uuid.uuid4().hex[:8]}@example.com"
    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": mgr_email, "full_name": "Team Lead", "role": "manager"},
    )
    manager_id = mgr_res.json()["id"]

    team_name = f"Frontend Squad {uuid.uuid4().hex[:6]}"
    create_res = await async_client.post(
        "/api/v1/teams",
        json={
            "name": team_name,
            "description": "Frontend development team",
            "manager_id": manager_id,
        },
    )
    assert create_res.status_code == 201
    team = create_res.json()
    assert team["name"] == team_name
    assert team["manager_id"] == manager_id
    assert "id" in team

    get_res = await async_client.get(f"/api/v1/teams/{team['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == team["id"]


@pytest.mark.asyncio
async def test_create_team_duplicate_name(async_client: AsyncClient):
    name = f"Unique Squad {uuid.uuid4().hex[:6]}"
    res1 = await async_client.post("/api/v1/teams", json={"name": name})
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/teams", json={"name": name})
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_team_membership_flow(async_client: AsyncClient):
    team_res = await async_client.post("/api/v1/teams", json={"name": f"Squad {uuid.uuid4().hex[:6]}"})
    team_id = team_res.json()["id"]

    user_res = await async_client.post(
        "/api/v1/users",
        json={
            "email": f"member_{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Squad Member",
            "role": "employee",
        },
    )
    user_id = user_res.json()["id"]

    add_res = await async_client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": user_id, "role_in_team": "developer"},
    )
    assert add_res.status_code == 201
    assert add_res.json()["team_id"] == team_id
    assert add_res.json()["user_id"] == user_id

    # Duplicate member returns 409
    dup_res = await async_client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"user_id": user_id, "role_in_team": "developer"},
    )
    assert dup_res.status_code == 409

    # List members
    list_res = await async_client.get(f"/api/v1/teams/{team_id}/members")
    assert list_res.status_code == 200
    members = list_res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == user_id

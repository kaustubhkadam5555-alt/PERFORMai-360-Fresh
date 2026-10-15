import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_user_success(async_client: AsyncClient):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "full_name": "Test User",
        "role": "employee",
        "is_active": True,
    }
    response = await async_client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == "Test User"
    assert data["role"] == "employee"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client: AsyncClient):
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "full_name": "Original User",
        "role": "employee",
    }
    res1 = await async_client.post("/api/v1/users", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/users", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_by_id(async_client: AsyncClient):
    email = f"find_{uuid.uuid4().hex[:8]}@example.com"
    create_res = await async_client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "Findable User", "role": "manager"},
    )
    user_id = create_res.json()["id"]

    get_res = await async_client.get(f"/api/v1/users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == user_id
    assert get_res.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_get_user_not_found(async_client: AsyncClient):
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/users/{random_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_users_with_filter(async_client: AsyncClient):
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    await async_client.post(
        "/api/v1/users",
        json={"email": email, "full_name": "Admin User", "role": "administrator"},
    )

    list_res = await async_client.get("/api/v1/users?role=administrator")
    assert list_res.status_code == 200
    users = list_res.json()
    assert len(users) >= 1
    assert all(u["role"] == "administrator" for u in users)

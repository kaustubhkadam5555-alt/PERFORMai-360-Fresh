from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness_root(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "PERFORMai-360"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_liveness_v1(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "PERFORMai-360"


@pytest.mark.asyncio
async def test_readiness_probe_live_database(async_client: AsyncClient):
    """Integration test: calls live /health/ready against actual running database."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"]["status"] == "ready"
    assert data["dependencies"]["database"]["message"] == "connected"
    assert data["dependencies"]["llm_provider"]["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_probe_database_mocked_healthy(async_client: AsyncClient):
    with patch(
        "app.api.v1.endpoints.health.check_database_connection",
        return_value=(True, "connected"),
    ):
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["database"]["status"] == "ready"
        assert data["dependencies"]["database"]["message"] == "connected"
        assert data["dependencies"]["llm_provider"]["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_probe_database_unhealthy(async_client: AsyncClient):
    with patch(
        "app.api.v1.endpoints.health.check_database_connection",
        return_value=(False, "Database connection unavailable (ConnectionRefusedError)"),
    ):
        response = await async_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unready"
        assert data["dependencies"]["database"]["status"] == "unhealthy"
        assert "ConnectionRefusedError" in data["dependencies"]["database"]["message"]


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "PERFORMai-360"
    assert data["api_v1"] == "/api/v1"

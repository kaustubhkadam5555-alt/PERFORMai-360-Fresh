import uuid
from datetime import date, timedelta
from typing import Any, Dict

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.fixture
async def setup_analysis_environment(async_client: AsyncClient) -> Dict[str, Any]:
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dev Diana", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Mark", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Diana 2026 Annual Review",
            "employee_id": employee_id,
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    cycle_id = cycle_res.json()["id"]

    # Register sample evidence
    today = date.today()
    pr_res = await async_client.post(
        "/api/v1/evidence",
        json={
            "cycle_id": cycle_id,
            "title": "PR #310: Real-time telemetry pipeline optimization",
            "source_type": "pull_request",
            "source_date": (today - timedelta(days=20)).isoformat(),
            "storage_reference": "github/pulls/310",
            "metadata_json": {
                "snippet": "Reduced telemetry message latency by 45% using batch buffering.",
            },
            "access_policy": "internal",
        },
    )
    pr_id = pr_res.json()["id"]

    doc_res = await async_client.post(
        "/api/v1/evidence",
        json={
            "cycle_id": cycle_id,
            "title": "RFC: Distributed Transaction Orchestration",
            "source_type": "document",
            "source_date": (today - timedelta(days=40)).isoformat(),
            "storage_reference": "wiki/rfc-transaction-orchestration",
            "metadata_json": {
                "snippet": "Proposed saga pattern for multi-region microservices.",
            },
            "access_policy": "internal",
        },
    )
    doc_id = doc_res.json()["id"]

    return {
        "employee_id": employee_id,
        "owner_id": owner_id,
        "cycle_id": cycle_id,
        "evidence_ids": [pr_id, doc_id],
    }


@pytest.mark.asyncio
async def test_execute_review_analysis_success(async_client: AsyncClient, setup_analysis_environment):
    env = setup_analysis_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    # 1. Execute analysis
    response = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        json={"max_evidence_items": 50, "include_draft_report": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["cycle_id"] == cycle_id
    assert data["status"] == "completed"
    assert data["requires_human_review"] is True
    assert "human_review_notice" in data
    assert "evidence-grounded AI decision support draft" in data["human_review_notice"]

    # Verify evidence summary
    assert data["evidence_summary"]["total_evidence_examined"] == 2
    assert len(data["evidence_summary"]["cited_evidence_ids"]) > 0

    # Verify strengths with grounded citations
    assert len(data["strengths"]) > 0
    for s in data["strengths"]:
        assert len(s["supporting_evidence_ids"]) > 0
        for eid in s["supporting_evidence_ids"]:
            assert eid in env["evidence_ids"]

    # Verify suggested discussion questions
    assert len(data["suggested_discussion_questions"]) > 0

    analysis_id = data["analysis_id"]

    # 2. Retrieve analysis by ID
    get_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/analysis/{analysis_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["analysis_id"] == analysis_id
    assert get_data["status"] == "completed"

    # 3. Retrieve latest analysis for cycle
    latest_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        headers=headers,
    )
    assert latest_res.status_code == 200
    assert latest_res.json()["analysis_id"] == analysis_id

    # 4. Retrieve atomic findings
    findings_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/findings",
        headers=headers,
    )
    assert findings_res.status_code == 200
    findings = findings_res.json()
    assert len(findings) > 0
    assert any(f["finding_type"] == "strength" for f in findings)


@pytest.mark.asyncio
async def test_analysis_runs_alias_endpoint(async_client: AsyncClient, setup_analysis_environment):
    env = setup_analysis_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]
    headers = {"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"}

    response = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis-runs",
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_analysis_insufficient_evidence(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"empty_emp_{uuid.uuid4().hex[:6]}@example.com", "full_name": "Dev Empty", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={
            "email": f"empty_mgr_{uuid.uuid4().hex[:6]}@example.com",
            "full_name": "Manager Empty",
            "role": "manager",
        },
    )
    owner_id = mgr_res.json()["id"]

    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Empty Review Cycle",
            "employee_id": employee_id,
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    cycle_id = cycle_res.json()["id"]

    response = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        headers={"X-Viewer-Role": "manager"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["strengths"] == []
    assert data["improvement_opportunities"] == []
    assert len(data["suggested_discussion_questions"]) > 0
    assert any("No verified evidence" in lim for lim in data["overall_limitations"])


@pytest.mark.asyncio
async def test_cross_cycle_isolation(async_client: AsyncClient, setup_analysis_environment):
    env = setup_analysis_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]

    # Run analysis on Cycle 1
    run_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        headers={"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"},
    )
    analysis_id = run_res.json()["analysis_id"]

    # Create unrelated cycle 2
    cycle2_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Other Review Cycle",
            "employee_id": env["employee_id"],
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    cycle2_id = cycle2_res.json()["id"]

    # Attempt to retrieve Cycle 1's analysis through Cycle 2's route
    leak_res = await async_client.get(
        f"/api/v1/review-cycles/{cycle2_id}/analysis/{analysis_id}",
        headers={"X-Viewer-Role": "manager"},
    )
    assert leak_res.status_code == 404
    assert "does not belong" in leak_res.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_user_access_blocked(async_client: AsyncClient, setup_analysis_environment):
    env = setup_analysis_environment
    cycle_id = env["cycle_id"]

    unauthorized_user_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"stranger_{uuid.uuid4().hex[:6]}@example.com", "full_name": "Stranger Sam", "role": "employee"},
    )
    stranger_id = unauthorized_user_res.json()["id"]

    forbidden_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        headers={"X-Viewer-Id": stranger_id, "X-Viewer-Role": "employee"},
    )
    assert forbidden_res.status_code == 403


@pytest.mark.asyncio
async def test_disabled_provider_failure_handling(async_client: AsyncClient, setup_analysis_environment, monkeypatch):
    env = setup_analysis_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]

    # Set LLM_PROVIDER to "none"
    monkeypatch.setattr(settings, "LLM_PROVIDER", "none")

    response = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/analysis",
        headers={"X-Viewer-Id": owner_id, "X-Viewer-Role": "manager"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert any("unavailable or unconfigured" in lim for lim in data["overall_limitations"])

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_evidence_environment(async_client: AsyncClient):
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"emp_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dev Evan", "role": "employee"},
    )
    employee_id = emp_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"mgr_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Manager Martha", "role": "manager"},
    )
    owner_id = mgr_res.json()["id"]

    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Evan 2026 Review Cycle",
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
async def test_register_and_list_evidence(async_client: AsyncClient, setup_evidence_environment):
    env = setup_evidence_environment
    cycle_id = env["cycle_id"]
    employee_id = env["employee_id"]

    today = date.today()

    # 1. Register PR evidence
    pr_payload = {
        "title": "PR #412: High-throughput Kafka ingestion pipeline",
        "source_type": "pull_request",
        "source_date": (today - timedelta(days=10)).isoformat(),
        "storage_reference": "github/pulls/412",
        "metadata_json": {
            "pr_number": 412,
            "lines_changed": 350,
            "reviewers": ["reviewer1", "reviewer2"],
            "url": "https://github.com/org/repo/pull/412",
        },
        "access_policy": "internal",
    }
    pr_res = await async_client.post(f"/api/v1/review-cycles/{cycle_id}/evidence", json=pr_payload)
    assert pr_res.status_code == 201
    pr_ev = pr_res.json()
    assert pr_ev["title"] == "PR #412: High-throughput Kafka ingestion pipeline"
    assert pr_ev["source_type"] == "pull_request"
    pr_ev_id = pr_ev["id"]

    # 2. Register Design Doc evidence
    doc_payload = {
        "title": "RFC 89: Distributed Rate Limiter Architecture",
        "source_type": "design_doc",
        "source_date": (today - timedelta(days=30)).isoformat(),
        "storage_reference": "docs/rfc-89.md",
        "access_policy": "internal",
    }
    doc_res = await async_client.post(f"/api/v1/review-cycles/{cycle_id}/evidence", json=doc_payload)
    assert doc_res.status_code == 201
    doc_ev_id = doc_res.json()["id"]

    # 3. Retrieve evidence by ID
    get_res = await async_client.get(f"/api/v1/evidence/{pr_ev_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == pr_ev_id
    assert get_res.json()["metadata_json"]["pr_number"] == 412

    # 4. List evidence filtered by source_type=pull_request
    list_pr = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/evidence",
        params={"source_type": "pull_request"},
    )
    assert list_pr.status_code == 200
    assert any(e["id"] == pr_ev_id for e in list_pr.json())
    assert not any(e["id"] == doc_ev_id for e in list_pr.json())

    # 5. List evidence by employee
    list_emp = await async_client.get(
        "/api/v1/evidence",
        params={"employee_id": employee_id},
    )
    assert list_emp.status_code == 200
    assert len(list_emp.json()) >= 2

    # 6. Update evidence
    patch_res = await async_client.patch(
        f"/api/v1/evidence/{pr_ev_id}",
        json={"title": "PR #412 (Merged): High-throughput Kafka ingestion pipeline"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "PR #412 (Merged): High-throughput Kafka ingestion pipeline"

    # 7. Delete evidence
    del_res = await async_client.delete(f"/api/v1/evidence/{pr_ev_id}")
    assert del_res.status_code == 204

    # 8. Verify deletion
    verify_res = await async_client.get(f"/api/v1/evidence/{pr_ev_id}")
    assert verify_res.status_code == 404


@pytest.mark.asyncio
async def test_evidence_access_policy_and_validation(async_client: AsyncClient, setup_evidence_environment):
    env = setup_evidence_environment
    cycle_id = env["cycle_id"]
    owner_id = env["owner_id"]

    # 1. Invalid source type rejected
    bad_source = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/evidence",
        json={"title": "Invalid source", "source_type": "invalid_source_type"},
    )
    assert bad_source.status_code == 422

    # 2. Path traversal in storage_reference rejected
    bad_path = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/evidence",
        json={
            "title": "Traversal exploit attempt",
            "storage_reference": "../../../etc/passwd",
        },
    )
    assert bad_path.status_code == 422

    # 3. Confidential evidence visibility check
    conf_payload = {
        "title": "Confidential Performance Note",
        "source_type": "note",
        "access_policy": "manager_only",
    }
    conf_res = await async_client.post(f"/api/v1/review-cycles/{cycle_id}/evidence", json=conf_payload)
    assert conf_res.status_code == 201
    conf_id = conf_res.json()["id"]

    # Anonymous / employee viewer cannot see manager_only evidence
    anon_list = await async_client.get(f"/api/v1/review-cycles/{cycle_id}/evidence")
    assert not any(e["id"] == conf_id for e in anon_list.json())

    # Manager / owner can see manager_only evidence
    mgr_list = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/evidence",
        params={"viewer_id": owner_id, "viewer_role": "manager"},
    )
    assert any(e["id"] == conf_id for e in mgr_list.json())

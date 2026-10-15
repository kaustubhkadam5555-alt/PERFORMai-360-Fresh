import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_two_employees_env(async_client: AsyncClient):
    # Employee Alice
    alice_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"alice_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Alice Dev", "role": "employee"},
    )
    alice_id = alice_res.json()["id"]

    # Employee Bob
    bob_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"bob_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Bob Dev", "role": "employee"},
    )
    bob_id = bob_res.json()["id"]

    # Manager Carol
    carol_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"carol_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Carol Manager", "role": "manager"},
    )
    carol_id = carol_res.json()["id"]

    # Admin Dave
    dave_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"dave_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Dave Admin", "role": "administrator"},
    )
    admin_id = dave_res.json()["id"]

    # Review cycle for Alice
    cycle_a_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Alice 2026 Cycle",
            "employee_id": alice_id,
            "owner_id": carol_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    cycle_a_id = cycle_a_res.json()["id"]

    # Review cycle for Bob
    cycle_b_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Bob 2026 Cycle",
            "employee_id": bob_id,
            "owner_id": carol_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    cycle_b_id = cycle_b_res.json()["id"]

    return {
        "alice_id": alice_id,
        "bob_id": bob_id,
        "carol_id": carol_id,
        "admin_id": admin_id,
        "cycle_a_id": cycle_a_id,
        "cycle_b_id": cycle_b_id,
    }


@pytest.mark.asyncio
async def test_content_retrieval_and_download(async_client: AsyncClient, setup_two_employees_env):
    env = setup_two_employees_env
    cycle_a_id = env["cycle_a_id"]
    alice_id = env["alice_id"]

    # Upload document for Alice
    doc_content = b"Content retrieval test document for Alice's cycle."
    files = {"file": ("alice_notes.txt", doc_content, "text/plain")}
    data = {
        "title": "Alice Notes",
        "access_policy": "internal",
    }
    upload_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_a_id}/evidence/upload",
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201
    evidence_id = upload_res.json()["id"]

    # Alice retrieves content as attachment
    get_res = await async_client.get(
        f"/api/v1/evidence/{evidence_id}/content",
        params={"viewer_id": alice_id, "download": "true"},
    )
    assert get_res.status_code == 200
    assert get_res.content == doc_content
    assert "attachment" in get_res.headers.get("content-disposition", "")
    assert "alice_notes.txt" in get_res.headers.get("content-disposition", "")

    # Alice views content inline
    inline_res = await async_client.get(
        f"/api/v1/evidence/{evidence_id}/content",
        params={"viewer_id": alice_id, "download": "false"},
    )
    assert inline_res.status_code == 200
    assert inline_res.content == doc_content
    assert "attachment" not in inline_res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_cross_employee_isolation(async_client: AsyncClient, setup_two_employees_env):
    env = setup_two_employees_env
    cycle_a_id = env["cycle_a_id"]
    alice_id = env["alice_id"]
    bob_id = env["bob_id"]
    carol_id = env["carol_id"]
    admin_id = env["admin_id"]

    # Upload internal document for Alice
    doc_content = b"Alice's confidential work log."
    files = {"file": ("work_log.txt", doc_content, "text/plain")}
    data = {"title": "Alice Work Log", "access_policy": "internal"}
    upload_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_a_id}/evidence/upload",
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201
    alice_ev_id = upload_res.json()["id"]

    # 1. Bob (unrelated employee) attempts to access Alice's evidence by ID -> 404 (isolated)
    bob_get = await async_client.get(
        f"/api/v1/evidence/{alice_ev_id}",
        params={"viewer_id": bob_id, "viewer_role": "employee"},
    )
    assert bob_get.status_code == 404

    # 2. Bob attempts to download Alice's content -> 404 (isolated)
    bob_download = await async_client.get(
        f"/api/v1/evidence/{alice_ev_id}/content",
        params={"viewer_id": bob_id, "viewer_role": "employee"},
    )
    assert bob_download.status_code == 404

    # 3. Bob queries Alice's cycle evidence list -> empty list returned
    bob_list = await async_client.get(
        f"/api/v1/review-cycles/{cycle_a_id}/evidence",
        params={"viewer_id": bob_id, "viewer_role": "employee"},
    )
    assert bob_list.status_code == 200
    assert not any(item["id"] == alice_ev_id for item in bob_list.json())

    # 4. Alice accesses her own evidence -> 200
    alice_get = await async_client.get(
        f"/api/v1/evidence/{alice_ev_id}",
        params={"viewer_id": alice_id, "viewer_role": "employee"},
    )
    assert alice_get.status_code == 200

    # 5. Carol (manager / cycle owner) accesses Alice's evidence -> 200
    carol_get = await async_client.get(
        f"/api/v1/evidence/{alice_ev_id}",
        params={"viewer_id": carol_id, "viewer_role": "manager"},
    )
    assert carol_get.status_code == 200

    # 6. Admin Dave accesses Alice's evidence -> 200
    admin_get = await async_client.get(
        f"/api/v1/evidence/{alice_ev_id}",
        params={"viewer_id": admin_id, "viewer_role": "administrator"},
    )
    assert admin_get.status_code == 200


@pytest.mark.asyncio
async def test_manager_only_evidence_hidden_from_subject_employee(async_client: AsyncClient, setup_two_employees_env):
    env = setup_two_employees_env
    cycle_a_id = env["cycle_a_id"]
    alice_id = env["alice_id"]
    carol_id = env["carol_id"]

    # Upload manager_only document to Alice's cycle
    files = {"file": ("manager_evaluation.txt", b"Private managerial notes on Alice", "text/plain")}
    data = {
        "title": "Managerial Evaluation Note",
        "access_policy": "manager_only",
    }
    upload_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_a_id}/evidence/upload",
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201
    mgr_ev_id = upload_res.json()["id"]

    # Alice (subject employee) attempts to get manager_only evidence -> 404 (hidden)
    alice_get = await async_client.get(
        f"/api/v1/evidence/{mgr_ev_id}",
        params={"viewer_id": alice_id, "viewer_role": "employee"},
    )
    assert alice_get.status_code == 404

    # Alice attempts to download content -> 404
    alice_download = await async_client.get(
        f"/api/v1/evidence/{mgr_ev_id}/content",
        params={"viewer_id": alice_id, "viewer_role": "employee"},
    )
    assert alice_download.status_code == 404

    # Carol (manager) accesses manager_only evidence -> 200
    carol_get = await async_client.get(
        f"/api/v1/evidence/{mgr_ev_id}",
        params={"viewer_id": carol_id, "viewer_role": "manager"},
    )
    assert carol_get.status_code == 200


@pytest.mark.asyncio
async def test_cycle_evidence_completeness_and_gap_detection(async_client: AsyncClient, setup_two_employees_env):
    env = setup_two_employees_env
    cycle_b_id = env["cycle_b_id"]
    carol_id = env["carol_id"]

    # 1. Empty cycle completeness check
    empty_comp = await async_client.get(
        f"/api/v1/review-cycles/{cycle_b_id}/evidence/completeness",
        params={"viewer_id": carol_id, "viewer_role": "manager"},
    )
    assert empty_comp.status_code == 200
    data = empty_comp.json()
    assert data["total_evidence_count"] == 0
    assert data["completeness_score"] == 0.0
    assert any("No evidence records attached" in gap for gap in data["detected_gaps"])

    # 2. Add only PR evidence (missing technical design docs)
    await async_client.post(
        f"/api/v1/review-cycles/{cycle_b_id}/evidence",
        json={
            "title": "PR #100 Core Engine",
            "source_type": "pull_request",
            "source_date": "2026-06-01",
            "access_policy": "internal",
        },
    )
    pr_comp = await async_client.get(
        f"/api/v1/review-cycles/{cycle_b_id}/evidence/completeness",
        params={"viewer_id": carol_id, "viewer_role": "manager"},
    )
    assert pr_comp.status_code == 200
    data = pr_comp.json()
    assert data["total_evidence_count"] == 1
    assert any("Missing technical design documentation" in gap for gap in data["detected_gaps"])

    # 3. Add design doc and evidence spread across the cycle
    await async_client.post(
        f"/api/v1/review-cycles/{cycle_b_id}/evidence",
        json={
            "title": "RFC 10 High-Level Architecture",
            "source_type": "design_doc",
            "source_date": "2026-02-15",
            "access_policy": "internal",
        },
    )
    balanced_comp = await async_client.get(
        f"/api/v1/review-cycles/{cycle_b_id}/evidence/completeness",
        params={"viewer_id": carol_id, "viewer_role": "manager"},
    )
    assert balanced_comp.status_code == 200
    data = balanced_comp.json()
    assert data["total_evidence_count"] == 2
    assert data["completeness_score"] >= 0.8
    assert not any("Missing technical design" in gap for gap in data["detected_gaps"])
    assert not any("Missing code delivery" in gap for gap in data["detected_gaps"])
    assert data["has_recency_bias_risk"] is False

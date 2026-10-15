import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_feedback_environment(async_client: AsyncClient):
    # Create employee (Bob), peer (Charlie), manager (Alice)
    emp_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"bob_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Bob Employee", "role": "employee"},
    )
    bob_id = emp_res.json()["id"]

    peer_res = await async_client.post(
        "/api/v1/users",
        json={
            "email": f"charlie_{uuid.uuid4().hex[:8]}@example.com",
            "full_name": "Charlie Peer",
            "role": "peer_reviewer",
        },
    )
    charlie_id = peer_res.json()["id"]

    mgr_res = await async_client.post(
        "/api/v1/users",
        json={"email": f"alice_{uuid.uuid4().hex[:8]}@example.com", "full_name": "Alice Manager", "role": "manager"},
    )
    alice_id = mgr_res.json()["id"]

    # Create cycle for Bob
    cycle_res = await async_client.post(
        "/api/v1/review-cycles",
        json={
            "title": "Bob H1 Review",
            "employee_id": bob_id,
            "owner_id": alice_id,
            "period_start": "2026-01-01",
            "period_end": "2026-06-30",
        },
    )
    cycle_id = cycle_res.json()["id"]

    return {
        "bob_id": bob_id,
        "charlie_id": charlie_id,
        "alice_id": alice_id,
        "cycle_id": cycle_id,
    }


@pytest.mark.asyncio
async def test_feedback_submission_requires_active_cycle(async_client: AsyncClient, setup_feedback_environment):
    env = setup_feedback_environment
    cycle_id = env["cycle_id"]
    bob_id = env["bob_id"]

    # Cycle is currently draft -> submission should be rejected with 409
    res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": bob_id,
            "subject_employee_id": bob_id,
            "feedback_type": "self",
            "content": "My self assessment for H1",
        },
    )
    assert res.status_code == 409
    assert "Feedback submissions are only permitted for active review cycles" in res.json()["detail"]

    # Activate cycle
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})

    # Now self feedback submission succeeds
    res2 = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": bob_id,
            "subject_employee_id": bob_id,
            "feedback_type": "self",
            "content": "My self assessment for H1",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["feedback_type"] == "self"
    assert res2.json()["content"] == "My self assessment for H1"


@pytest.mark.asyncio
async def test_feedback_author_subject_relationship_rules(async_client: AsyncClient, setup_feedback_environment):
    env = setup_feedback_environment
    cycle_id = env["cycle_id"]
    bob_id = env["bob_id"]
    charlie_id = env["charlie_id"]

    # Activate cycle
    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})

    # 1. Invalid self feedback: author is Charlie, but subject is Bob -> 422
    bad_self = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": charlie_id,
            "subject_employee_id": bob_id,
            "feedback_type": "self",
            "content": "Self feedback with wrong author",
        },
    )
    assert bad_self.status_code == 422

    # 2. Invalid peer feedback: author is Bob and subject is Bob -> 422
    bad_peer = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": bob_id,
            "subject_employee_id": bob_id,
            "feedback_type": "peer",
            "content": "Peer feedback on myself",
        },
    )
    assert bad_peer.status_code == 422

    # 3. Valid peer feedback: Charlie on Bob -> 201
    good_peer = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": charlie_id,
            "subject_employee_id": bob_id,
            "feedback_type": "peer",
            "content": "Bob was an outstanding collaborator on project Athena.",
            "category": "collaboration",
        },
    )
    assert good_peer.status_code == 201
    assert good_peer.json()["author_id"] == charlie_id


@pytest.mark.asyncio
async def test_feedback_missing_references(async_client: AsyncClient, setup_feedback_environment):
    env = setup_feedback_environment
    cycle_id = env["cycle_id"]
    bob_id = env["bob_id"]

    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})

    # Non-existent cycle
    bad_cycle_id = str(uuid.uuid4())
    res1 = await async_client.post(
        f"/api/v1/review-cycles/{bad_cycle_id}/feedback",
        json={
            "author_id": bob_id,
            "subject_employee_id": bob_id,
            "feedback_type": "self",
            "content": "Self assessment",
        },
    )
    assert res1.status_code == 404

    # Non-existent author
    bad_author_id = str(uuid.uuid4())
    res2 = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": bad_author_id,
            "subject_employee_id": bob_id,
            "feedback_type": "peer",
            "content": "Peer feedback",
        },
    )
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_feedback_visibility_rules(async_client: AsyncClient, setup_feedback_environment):
    env = setup_feedback_environment
    cycle_id = env["cycle_id"]
    bob_id = env["bob_id"]
    charlie_id = env["charlie_id"]
    alice_id = env["alice_id"]

    await async_client.patch(f"/api/v1/review-cycles/{cycle_id}", json={"status": "active"})

    # Charlie submits manager_only feedback for Bob
    mgr_only_res = await async_client.post(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        json={
            "author_id": charlie_id,
            "subject_employee_id": bob_id,
            "feedback_type": "peer",
            "content": "Manager-confidential observation regarding Bob.",
            "visibility": "manager_only",
        },
    )
    assert mgr_only_res.status_code == 201
    fb_id = mgr_only_res.json()["id"]

    # 1. Unauthenticated / anonymous viewer lists feedback -> manager_only is hidden
    list_anon = await async_client.get(f"/api/v1/review-cycles/{cycle_id}/feedback")
    assert list_anon.status_code == 200
    assert not any(fb["id"] == fb_id for fb in list_anon.json())

    # 2. Bob (employee/subject) lists feedback -> manager_only is hidden
    list_bob = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        params={"viewer_id": bob_id, "viewer_role": "employee"},
    )
    assert list_bob.status_code == 200
    assert not any(fb["id"] == fb_id for fb in list_bob.json())

    # 3. Bob attempts to get the specific manager_only feedback by ID -> returns 404 (hidden)
    get_bob = await async_client.get(
        f"/api/v1/feedback/{fb_id}",
        params={"viewer_id": bob_id, "viewer_role": "employee"},
    )
    assert get_bob.status_code == 404

    # 4. Charlie (author) gets it by ID -> 200 OK
    get_charlie = await async_client.get(
        f"/api/v1/feedback/{fb_id}",
        params={"viewer_id": charlie_id},
    )
    assert get_charlie.status_code == 200

    # 5. Alice (cycle owner/manager) lists feedback -> manager_only is visible
    list_alice = await async_client.get(
        f"/api/v1/review-cycles/{cycle_id}/feedback",
        params={"viewer_id": alice_id, "viewer_role": "manager"},
    )
    assert list_alice.status_code == 200
    assert any(fb["id"] == fb_id for fb in list_alice.json())

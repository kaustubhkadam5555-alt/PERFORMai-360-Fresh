import uuid
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import EvidenceContextBuilder
from app.models.evidence import Evidence, EvidenceAccessPolicy, EvidenceSourceType
from app.models.review_cycle import ReviewCycle
from app.models.user import User


@pytest.mark.asyncio
async def test_context_builder_cycle_scoping(db_session: AsyncSession):
    # 1. Create employees
    emp_a = User(email=f"emp_a_{uuid.uuid4().hex[:6]}@example.com", full_name="Alice Developer", role="employee")
    emp_b = User(email=f"emp_b_{uuid.uuid4().hex[:6]}@example.com", full_name="Bob Engineer", role="employee")
    db_session.add_all([emp_a, emp_b])
    await db_session.commit()
    await db_session.refresh(emp_a)
    await db_session.refresh(emp_b)

    # 2. Create cycles
    cycle_a = ReviewCycle(
        title="Alice H1 Review",
        employee_id=emp_a.id,
        owner_id=emp_a.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    cycle_b = ReviewCycle(
        title="Bob H1 Review",
        employee_id=emp_b.id,
        owner_id=emp_b.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    db_session.add_all([cycle_a, cycle_b])
    await db_session.commit()
    await db_session.refresh(cycle_a)
    await db_session.refresh(cycle_b)

    # 3. Add evidence to Cycle A and Cycle B
    ev_a = Evidence(
        cycle_id=cycle_a.id,
        source_type=EvidenceSourceType.PULL_REQUEST.value,
        title="PR #100: Alice Payment Gateway",
        storage_reference="github/pulls/100",
        source_date=date(2026, 3, 1),
        metadata_json={"snippet": "Merged high-throughput payment handler."},
        access_policy=EvidenceAccessPolicy.INTERNAL.value,
    )
    ev_b = Evidence(
        cycle_id=cycle_b.id,
        source_type=EvidenceSourceType.PULL_REQUEST.value,
        title="PR #200: Bob Search Indexer",
        storage_reference="github/pulls/200",
        source_date=date(2026, 3, 2),
        metadata_json={"snippet": "Elasticsearch migration."},
        access_policy=EvidenceAccessPolicy.INTERNAL.value,
    )
    db_session.add_all([ev_a, ev_b])
    await db_session.commit()
    await db_session.refresh(ev_a)
    await db_session.refresh(ev_b)

    # 4. Build context for Cycle A
    builder = EvidenceContextBuilder(db_session)
    context_a = await builder.build_context(cycle_id=cycle_a.id, viewer_role="manager")

    # Assertions: Cycle A context contains ev_a, NOT ev_b
    assert len(context_a.evidence_items) == 1
    assert context_a.evidence_items[0].id == ev_a.id
    assert ev_a.id in context_a.valid_evidence_ids
    assert ev_b.id not in context_a.valid_evidence_ids
    assert context_a.employee_name == "Alice Developer"
    assert "<untrusted_evidence_document" in context_a.prompt_context_text
    assert str(ev_a.id) in context_a.prompt_context_text
    assert str(ev_b.id) not in context_a.prompt_context_text


@pytest.mark.asyncio
async def test_context_builder_bounding_and_truncation(db_session: AsyncSession):
    emp = User(email=f"emp_{uuid.uuid4().hex[:6]}@example.com", full_name="Charlie Dev", role="employee")
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)

    cycle = ReviewCycle(
        title="Charlie Review",
        employee_id=emp.id,
        owner_id=emp.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    # Add 5 evidence items with substantial content
    for i in range(5):
        ev = Evidence(
            cycle_id=cycle.id,
            source_type=EvidenceSourceType.DOCUMENT_UPLOAD.value,
            title=f"Doc {i}: Large Technical RFC",
            storage_reference=f"docs/rfc_{i}",
            source_date=date(2026, 2, i + 1),
            metadata_json={"snippet": "Long technical text " * 50},
            access_policy=EvidenceAccessPolicy.INTERNAL.value,
        )
        db_session.add(ev)
    await db_session.commit()

    builder = EvidenceContextBuilder(db_session)

    # Test max_items bounding
    bounded_items_ctx = await builder.build_context(cycle_id=cycle.id, max_items=2, viewer_role="manager")
    assert len(bounded_items_ctx.evidence_items) == 2
    assert bounded_items_ctx.truncated is True

    # Test max_chars bounding
    bounded_chars_ctx = await builder.build_context(cycle_id=cycle.id, max_chars=150, viewer_role="manager")
    assert bounded_chars_ctx.truncated is True
    assert bounded_chars_ctx.total_characters <= 350


@pytest.mark.asyncio
async def test_context_builder_nonexistent_cycle(db_session: AsyncSession):
    builder = EvidenceContextBuilder(db_session)
    random_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        await builder.build_context(cycle_id=random_id)
    assert exc_info.value.status_code == 404

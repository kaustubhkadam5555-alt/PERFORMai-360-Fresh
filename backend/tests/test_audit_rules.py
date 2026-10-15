import uuid
from datetime import date, timedelta

from app.audit.base import AuditContext
from app.audit.rules.contradictions import ContradictoryFeedbackRule
from app.audit.rules.evidence_coverage import EvidenceCoverageRule
from app.audit.rules.recency_concentration import RecencyConcentrationRule
from app.audit.rules.stakeholder_coverage import StakeholderCoverageRule
from app.audit.rules.vague_language import VagueLanguageRule
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.finding import Finding
from app.models.review_cycle import ReviewCycle


def _create_mock_cycle(days: int = 180) -> ReviewCycle:
    return ReviewCycle(
        id=uuid.uuid4(),
        title="Engineering Review Cycle",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 1) + timedelta(days=days),
    )


# --- Rule 1: Evidence Coverage ---


def test_evidence_coverage_empty_cycle():
    cycle = _create_mock_cycle()
    ctx = AuditContext(cycle=cycle, evidence_items=[])
    rule = EvidenceCoverageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 1
    assert flags[0].flag_type == "evidence_coverage"
    assert flags[0].severity == "high"
    assert "zero verified evidence records" in flags[0].explanation


def test_evidence_coverage_unsupported_findings():
    cycle = _create_mock_cycle()
    ev = Evidence(id=uuid.uuid4(), cycle_id=cycle.id, title="PR #1", source_type="pr")
    f_unsupported = Finding(
        id=uuid.uuid4(),
        cycle_id=cycle.id,
        statement="Built entire payment system single-handedly",
        finding_type="strength",
        evidence_ids=[],
        validation_status="unverified",
    )
    ctx = AuditContext(cycle=cycle, evidence_items=[ev], findings=[f_unsupported])
    rule = EvidenceCoverageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 1
    assert flags[0].severity == "review"
    assert "without verifiable source evidence" in flags[0].explanation


# --- Rule 2: Recency Concentration ---


def test_recency_concentration_detected():
    cycle = _create_mock_cycle(days=120)  # Jan 1 to May 1
    # Create 4 evidence items, all in late April (final 25%)
    late_date = cycle.period_end - timedelta(days=5)
    evs = [
        Evidence(id=uuid.uuid4(), cycle_id=cycle.id, title=f"Doc {i}", source_type="pr", source_date=late_date)
        for i in range(4)
    ]
    ctx = AuditContext(cycle=cycle, evidence_items=evs)
    rule = RecencyConcentrationRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 1
    assert flags[0].flag_type == "recency_concentration"
    assert flags[0].severity == "medium"
    assert "recency concentration detected" in flags[0].explanation


def test_recency_concentration_balanced():
    cycle = _create_mock_cycle(days=120)
    # Balanced evidence distributed across January, March, and April
    ev1 = Evidence(id=uuid.uuid4(), cycle_id=cycle.id, title="PR 1", source_type="pr", source_date=date(2026, 1, 15))
    ev2 = Evidence(id=uuid.uuid4(), cycle_id=cycle.id, title="PR 2", source_type="pr", source_date=date(2026, 2, 20))
    ev3 = Evidence(id=uuid.uuid4(), cycle_id=cycle.id, title="PR 3", source_type="pr", source_date=date(2026, 4, 25))

    ctx = AuditContext(cycle=cycle, evidence_items=[ev1, ev2, ev3])
    rule = RecencyConcentrationRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 0


# --- Rule 3: Stakeholder Coverage ---


def test_stakeholder_coverage_missing_self_and_peer():
    cycle = _create_mock_cycle()
    mgr_fb = Feedback(
        id=uuid.uuid4(),
        cycle_id=cycle.id,
        author_id=uuid.uuid4(),
        feedback_type="manager",
        content="Solid engineering execution.",
    )
    ctx = AuditContext(cycle=cycle, feedback_items=[mgr_fb])
    rule = StakeholderCoverageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 2
    types = [f.explanation for f in flags]
    assert any("lacks a self-assessment" in t for t in types)
    assert any("0 peer review submissions" in t for t in types)


def test_stakeholder_coverage_balanced():
    cycle = _create_mock_cycle()
    self_fb = Feedback(
        id=uuid.uuid4(), cycle_id=cycle.id, author_id=uuid.uuid4(), feedback_type="self", content="Self review"
    )
    peer_fb = Feedback(
        id=uuid.uuid4(), cycle_id=cycle.id, author_id=uuid.uuid4(), feedback_type="peer", content="Peer review"
    )
    mgr_fb = Feedback(
        id=uuid.uuid4(), cycle_id=cycle.id, author_id=uuid.uuid4(), feedback_type="manager", content="Manager review"
    )

    ctx = AuditContext(cycle=cycle, feedback_items=[self_fb, peer_fb, mgr_fb])
    rule = StakeholderCoverageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 0


# --- Rule 4: Vague or Absolute Language ---


def test_vague_language_detects_absolutes_and_pejoratives():
    cycle = _create_mock_cycle()
    fb1 = Feedback(
        id=uuid.uuid4(),
        cycle_id=cycle.id,
        feedback_type="peer",
        content="Alice always misses sprint planning and has a bad attitude.",
    )
    ctx = AuditContext(cycle=cycle, feedback_items=[fb1])
    rule = VagueLanguageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) >= 2
    explanations = [f.explanation for f in flags]
    assert any("always" in exp for exp in explanations)
    assert any("bad attitude" in exp for exp in explanations)


def test_vague_language_clean_behavioral_feedback():
    cycle = _create_mock_cycle()
    fb = Feedback(
        id=uuid.uuid4(),
        cycle_id=cycle.id,
        feedback_type="peer",
        content="Delivered Kafka batching optimization reducing tail latency by 30%.",
    )
    ctx = AuditContext(cycle=cycle, feedback_items=[fb])
    rule = VagueLanguageRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 0


# --- Rule 5: Contradictory Feedback ---


def test_contradictory_feedback_detected():
    cycle = _create_mock_cycle()
    eid = uuid.uuid4()
    cf = Finding(
        id=uuid.uuid4(),
        cycle_id=cycle.id,
        finding_type="contradiction",
        statement="Delivery Velocity: (A) Fast sprint turnarounds vs (B) Multiple PR review blockers.",
        evidence_ids=[str(eid)],
    )
    ctx = AuditContext(cycle=cycle, findings=[cf])
    rule = ContradictoryFeedbackRule()
    flags = rule.evaluate(ctx)

    assert len(flags) == 1
    assert flags[0].flag_type == "contradictory_feedback"
    assert flags[0].evidence_ids == [eid]
    assert "Contradictory performance observation" in flags[0].explanation

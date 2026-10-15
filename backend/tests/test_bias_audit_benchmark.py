import uuid
from datetime import date
from typing import Dict, List, Set

from app.audit.base import AuditContext
from app.audit.engine import AuditEngine
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.finding import Finding
from app.models.review_cycle import ReviewCycle


def _create_synthetic_benchmark() -> List[Dict[str, object]]:
    """
    Creates a synthetic labeled evaluation benchmark containing diverse review scenarios
    with known expected ground-truth bias and evidence-quality flags.
    """
    benchmark_cases = []

    # Case 1: Ground Truth Clean Baseline
    cycle_1 = ReviewCycle(
        id=uuid.uuid4(),
        title="Balanced Senior Engineer Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    evs_1 = [
        Evidence(id=uuid.uuid4(), cycle_id=cycle_1.id, title="PR #1", source_type="pr", source_date=date(2026, 1, 20)),
        Evidence(id=uuid.uuid4(), cycle_id=cycle_1.id, title="PR #2", source_type="pr", source_date=date(2026, 3, 15)),
        Evidence(
            id=uuid.uuid4(), cycle_id=cycle_1.id, title="Doc #1", source_type="document", source_date=date(2026, 5, 10)
        ),
    ]
    fb_1 = [
        Feedback(
            id=uuid.uuid4(), cycle_id=cycle_1.id, feedback_type="self", content="Delivered resilient API service."
        ),
        Feedback(
            id=uuid.uuid4(), cycle_id=cycle_1.id, feedback_type="peer", content="Reviewed technical design proposal."
        ),
        Feedback(
            id=uuid.uuid4(),
            cycle_id=cycle_1.id,
            feedback_type="manager",
            content="Consistently met quarterly objectives.",
        ),
    ]
    findings_1 = [
        Finding(
            id=uuid.uuid4(),
            cycle_id=cycle_1.id,
            statement="Architected resilient API service",
            evidence_ids=[str(evs_1[0].id)],
        )
    ]
    benchmark_cases.append(
        {
            "name": "clean_baseline",
            "context": AuditContext(cycle=cycle_1, evidence_items=evs_1, feedback_items=fb_1, findings=findings_1),
            "expected_flag_types": set(),
        }
    )

    # Case 2: Recency Concentration
    cycle_2 = ReviewCycle(
        id=uuid.uuid4(),
        title="Recency Biased Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),  # 180 days
    )
    evs_2 = [
        Evidence(
            id=uuid.uuid4(), cycle_id=cycle_2.id, title=f"PR #{i}", source_type="pr", source_date=date(2026, 6, 20 + i)
        )
        for i in range(4)
    ]
    fb_2 = [
        Feedback(id=uuid.uuid4(), cycle_id=cycle_2.id, feedback_type="self", content="Shipped recent features."),
        Feedback(id=uuid.uuid4(), cycle_id=cycle_2.id, feedback_type="peer", content="Helped with release."),
    ]
    benchmark_cases.append(
        {
            "name": "recency_concentration",
            "context": AuditContext(cycle=cycle_2, evidence_items=evs_2, feedback_items=fb_2),
            "expected_flag_types": {"recency_concentration"},
        }
    )

    # Case 3: Missing Stakeholder Perspectives
    cycle_3 = ReviewCycle(
        id=uuid.uuid4(),
        title="Manager-Only Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    evs_3 = [
        Evidence(id=uuid.uuid4(), cycle_id=cycle_3.id, title="PR #10", source_type="pr", source_date=date(2026, 2, 10)),
        Evidence(id=uuid.uuid4(), cycle_id=cycle_3.id, title="PR #20", source_type="pr", source_date=date(2026, 4, 10)),
    ]
    fb_3 = [
        Feedback(id=uuid.uuid4(), cycle_id=cycle_3.id, feedback_type="manager", content="Manager review only."),
    ]
    benchmark_cases.append(
        {
            "name": "missing_stakeholders",
            "context": AuditContext(cycle=cycle_3, evidence_items=evs_3, feedback_items=fb_3),
            "expected_flag_types": {"stakeholder_coverage"},
        }
    )

    # Case 4: Vague Language and Pejoratives
    cycle_4 = ReviewCycle(
        id=uuid.uuid4(),
        title="Vague Claims Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    evs_4 = [
        Evidence(id=uuid.uuid4(), cycle_id=cycle_4.id, title="PR #1", source_type="pr", source_date=date(2026, 2, 1)),
        Evidence(id=uuid.uuid4(), cycle_id=cycle_4.id, title="PR #2", source_type="pr", source_date=date(2026, 4, 1)),
    ]
    fb_4 = [
        Feedback(id=uuid.uuid4(), cycle_id=cycle_4.id, feedback_type="self", content="Self review summary."),
        Feedback(
            id=uuid.uuid4(),
            cycle_id=cycle_4.id,
            feedback_type="peer",
            content="Alice always ignores PR comments and is lazy.",
        ),
    ]
    benchmark_cases.append(
        {
            "name": "vague_language",
            "context": AuditContext(cycle=cycle_4, evidence_items=evs_4, feedback_items=fb_4),
            "expected_flag_types": {"vague_or_absolute_claims"},
        }
    )

    # Case 5: Contradictory Feedback
    cycle_5 = ReviewCycle(
        id=uuid.uuid4(),
        title="Contradictory Feedback Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    evs_5 = [
        Evidence(id=uuid.uuid4(), cycle_id=cycle_5.id, title="PR #1", source_type="pr", source_date=date(2026, 2, 1)),
        Evidence(id=uuid.uuid4(), cycle_id=cycle_5.id, title="PR #2", source_type="pr", source_date=date(2026, 4, 1)),
    ]
    fb_5 = [
        Feedback(id=uuid.uuid4(), cycle_id=cycle_5.id, feedback_type="self", content="Self review summary."),
        Feedback(id=uuid.uuid4(), cycle_id=cycle_5.id, feedback_type="peer", content="Peer review summary."),
    ]
    findings_5 = [
        Finding(
            id=uuid.uuid4(),
            cycle_id=cycle_5.id,
            finding_type="contradiction",
            statement="Speed vs Quality: (A) Fast delivery vs (B) Multiple production regressions.",
            evidence_ids=[str(evs_5[0].id)],
        )
    ]
    benchmark_cases.append(
        {
            "name": "contradictions",
            "context": AuditContext(cycle=cycle_5, evidence_items=evs_5, feedback_items=fb_5, findings=findings_5),
            "expected_flag_types": {"contradictory_feedback"},
        }
    )

    # Case 6: Zero Evidence
    cycle_6 = ReviewCycle(
        id=uuid.uuid4(),
        title="Zero Evidence Review",
        employee_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
    )
    benchmark_cases.append(
        {
            "name": "zero_evidence",
            "context": AuditContext(cycle=cycle_6, evidence_items=[]),
            "expected_flag_types": {"evidence_coverage"},
        }
    )

    return benchmark_cases


def test_bias_audit_benchmark_evaluation():
    """
    Evaluates the AuditEngine against the synthetic labeled dataset and asserts
    grounding precision, recall, and F1 scores in accordance with PRD FR-09 and Section 13.
    """
    engine = AuditEngine()
    cases = _create_synthetic_benchmark()

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for case in cases:
        context = case["context"]
        expected_types: Set[str] = case["expected_flag_types"]  # type: ignore

        flags, health_score, is_ready = engine.run_audit(context)
        detected_types = {f.flag_type for f in flags}

        # Check for expected types
        for expected in expected_types:
            if expected in detected_types:
                true_positives += 1
            else:
                false_negatives += 1

        # Check for unexpected types
        for detected in detected_types:
            if detected not in expected_types:
                # Disregard stakeholder warnings if zero feedback was provided in zero_evidence case
                if case["name"] == "zero_evidence" and detected == "stakeholder_coverage":
                    continue
                false_positives += 1

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    # Output evaluation metric report
    print("\n--- Bias Audit Evaluation Benchmark Report ---")
    print(f"Total Scenarios Evaluated: {len(cases)}")
    print(f"True Positives: {true_positives}, False Positives: {false_positives}, False Negatives: {false_negatives}")
    print(f"Precision: {precision:.4f}, Recall: {recall:.4f}, F1-Score: {f1:.4f}")

    assert precision >= 0.95
    assert recall >= 0.95
    assert f1 >= 0.95

import uuid

from app.ai.validators import _sanitize_statement, validate_and_filter_citations


def test_sanitize_statement():
    dirty_text = "Clean engineering deliverable\x00\x08with control\x1f characters"
    cleaned = _sanitize_statement(dirty_text)
    assert cleaned == "Clean engineering deliverablewith control characters"
    assert _sanitize_statement(None) == ""
    assert _sanitize_statement(123) == ""


def test_validate_and_filter_citations_all_valid():
    valid_id1 = uuid.uuid4()
    valid_id2 = uuid.uuid4()
    valid_set = {valid_id1, valid_id2}

    raw_data = {
        "strengths": [
            {
                "title": "Robust API design",
                "description": "Implemented idempotent payment webhook endpoints.",
                "supporting_evidence_ids": [str(valid_id1)],
                "excerpts": ["Endpoint delivers 99.99% reliability"],
                "confidence": "high",
                "limitations": [],
            }
        ],
        "improvement_opportunities": [
            {
                "title": "Unit test coverage",
                "gap_observed": "Edge case test coverage fell below 80%.",
                "supporting_evidence_ids": [str(valid_id2)],
                "missing_context": "Refactor was expedited for hotfix.",
                "development_suggestion": "Add parameterized pytest suites for edge cases.",
            }
        ],
        "contradictions": [],
        "suggested_discussion_questions": [
            {
                "category": "architecture",
                "question": "What trade-offs influenced the webhook queuing architecture?",
                "context": "Observability showed minor message spikes.",
            }
        ],
        "overall_limitations": ["Limited load testing evidence."],
    }

    cleaned, warnings = validate_and_filter_citations(raw_data, valid_set)
    assert len(warnings) == 0
    assert len(cleaned["strengths"]) == 1
    assert cleaned["strengths"][0]["supporting_evidence_ids"] == [valid_id1]
    assert cleaned["strengths"][0]["confidence"] == "high"
    assert len(cleaned["improvement_opportunities"]) == 1
    assert cleaned["improvement_opportunities"][0]["supporting_evidence_ids"] == [valid_id2]


def test_validate_and_filter_citations_filters_hallucinated_ids():
    valid_id = uuid.uuid4()
    invented_id1 = uuid.uuid4()
    invented_id2 = "not-a-valid-uuid-1234"
    valid_set = {valid_id}

    raw_data = {
        "strengths": [
            {
                "title": "Kubernetes operator rollout",
                "description": "Migrated stateless microservices to container orchestration.",
                "supporting_evidence_ids": [str(valid_id), str(invented_id1), invented_id2],
                "confidence": "high",
                "limitations": [],
            },
            {
                "title": "Purely hallucinated contribution",
                "description": "Claim with zero grounded evidence in cycle.",
                "supporting_evidence_ids": [str(invented_id1)],
                "confidence": "high",
                "limitations": [],
            },
        ],
        "improvement_opportunities": [
            {
                "title": "Documentation gap",
                "gap_observed": "API schemas were undocumented.",
                "supporting_evidence_ids": [invented_id2],
                "development_suggestion": "Document OpenAPI specs.",
            }
        ],
        "contradictions": [],
        "suggested_discussion_questions": [],
        "overall_limitations": [],
    }

    cleaned, warnings = validate_and_filter_citations(raw_data, valid_set)

    # Warnings must capture filtered citations
    assert len(warnings) >= 2

    # First strength retains only the valid ID
    s1 = cleaned["strengths"][0]
    assert s1["supporting_evidence_ids"] == [valid_id]
    assert any("unverified evidence citation" in lim for lim in s1["limitations"])

    # Second strength had ONLY invalid IDs -> downgraded to low confidence
    s2 = cleaned["strengths"][1]
    assert s2["supporting_evidence_ids"] == []
    assert s2["confidence"] == "low"
    assert any("No verifiable source evidence attached" in lim for lim in s2["limitations"])

    # Improvement opportunity had invalid ID -> filtered out of supporting_evidence_ids
    imp = cleaned["improvement_opportunities"][0]
    assert imp["supporting_evidence_ids"] == []
    assert "ungrounded" in imp["missing_context"]

    # Overall limitations reflect audit findings
    assert any("Grounding audit flagged" in lim for lim in cleaned["overall_limitations"])

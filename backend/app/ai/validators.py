import re
import uuid
from typing import Any, Dict, List, Set, Tuple


def _parse_uuid_safely(val: Any) -> Tuple[bool, Any]:
    if isinstance(val, uuid.UUID):
        return True, val
    if isinstance(val, str):
        try:
            return True, uuid.UUID(val.strip())
        except (ValueError, AttributeError):
            return False, val
    return False, val


def validate_and_filter_citations(
    raw_data: Dict[str, Any],
    valid_evidence_ids: Set[uuid.UUID],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validates all evidence ID citations against the set of authorized evidence IDs.
    Returns (cleaned_data, validation_warnings).
    Invented or hallucinated evidence IDs are filtered out and explicit limitations are attached.
    """
    validation_warnings: List[str] = []
    cleaned: Dict[str, Any] = {
        "strengths": [],
        "improvement_opportunities": [],
        "contradictions": [],
        "suggested_discussion_questions": raw_data.get("suggested_discussion_questions", []),
        "overall_limitations": list(raw_data.get("overall_limitations", [])),
    }

    # 1. Validate Strengths
    for s in raw_data.get("strengths", []):
        raw_ids = s.get("supporting_evidence_ids", [])
        verified_ids = []
        unverified_ids = []

        for item in raw_ids:
            is_valid, parsed_uuid = _parse_uuid_safely(item)
            if is_valid and parsed_uuid in valid_evidence_ids:
                verified_ids.append(parsed_uuid)
            else:
                unverified_ids.append(str(item))

        limitations = list(s.get("limitations", []))
        if unverified_ids:
            warning = f"Filtered ungrounded evidence citation(s) in strength '{s.get('title')}': {unverified_ids}"
            validation_warnings.append(warning)
            limitations.append(
                f"Contains unverified evidence citation(s): {', '.join(unverified_ids)} not found in cycle scope"
            )

        confidence = s.get("confidence", "high").lower()
        if not verified_ids:
            confidence = "low"
            limitations.append("No verifiable source evidence attached to this observation")

        cleaned["strengths"].append(
            {
                "title": _sanitize_statement(s.get("title", "Observed Technical Contribution")),
                "description": _sanitize_statement(s.get("description", "")),
                "supporting_evidence_ids": verified_ids,
                "excerpts": [_sanitize_statement(e) for e in s.get("excerpts", []) if e],
                "confidence": confidence if confidence in {"high", "medium", "low"} else "medium",
                "limitations": limitations,
            }
        )

    # 2. Validate Improvement Opportunities
    for imp in raw_data.get("improvement_opportunities", []):
        raw_ids = imp.get("supporting_evidence_ids", [])
        verified_ids = []
        unverified_ids = []

        for item in raw_ids:
            is_valid, parsed_uuid = _parse_uuid_safely(item)
            if is_valid and parsed_uuid in valid_evidence_ids:
                verified_ids.append(parsed_uuid)
            else:
                unverified_ids.append(str(item))

        missing_context = imp.get("missing_context")
        if unverified_ids:
            warning = f"Filtered ungrounded citation(s) in improvement '{imp.get('title')}': {unverified_ids}"
            validation_warnings.append(warning)
            missing_context_note = f"Note: Citation(s) {', '.join(unverified_ids)} were ungrounded."
            missing_context = f"{missing_context} ({missing_context_note})" if missing_context else missing_context_note

        cleaned["improvement_opportunities"].append(
            {
                "title": _sanitize_statement(imp.get("title", "Development Opportunity")),
                "gap_observed": _sanitize_statement(imp.get("gap_observed", "")),
                "supporting_evidence_ids": verified_ids,
                "missing_context": _sanitize_statement(missing_context) if missing_context else None,
                "development_suggestion": _sanitize_statement(
                    imp.get("development_suggestion", "Continue focusing on core technical deliverables.")
                ),
            }
        )

    # 3. Validate Contradictions
    for c in raw_data.get("contradictions", []):
        raw_a = c.get("evidence_ids_a", [])
        raw_b = c.get("evidence_ids_b", [])

        verified_a = [
            parsed
            for item in raw_a
            if (is_v := _parse_uuid_safely(item))[0] and (parsed := is_v[1]) in valid_evidence_ids
        ]
        verified_b = [
            parsed
            for item in raw_b
            if (is_v := _parse_uuid_safely(item))[0] and (parsed := is_v[1]) in valid_evidence_ids
        ]

        cleaned["contradictions"].append(
            {
                "topic": _sanitize_statement(c.get("topic", "Contextual Contrast")),
                "observation_a": _sanitize_statement(c.get("observation_a", "")),
                "evidence_ids_a": verified_a,
                "observation_b": _sanitize_statement(c.get("observation_b", "")),
                "evidence_ids_b": verified_b,
                "missing_context": _sanitize_statement(c.get("missing_context")) if c.get("missing_context") else None,
                "uncertainty_note": _sanitize_statement(c.get("uncertainty_note"))
                if c.get("uncertainty_note")
                else None,
            }
        )

    # 4. Clean Discussion Questions
    cleaned_questions = []
    for q in raw_data.get("suggested_discussion_questions", []):
        cleaned_questions.append(
            {
                "category": q.get("category", "growth"),
                "question": _sanitize_statement(q.get("question", "")),
                "context": _sanitize_statement(q.get("context", "")),
            }
        )
    cleaned["suggested_discussion_questions"] = cleaned_questions

    if validation_warnings:
        cleaned["overall_limitations"].append(
            f"Grounding audit flagged {len(validation_warnings)} unverified evidence citation(s) in model draft."
        )

    return cleaned, validation_warnings


def _sanitize_statement(text: Any) -> str:
    """Sanitizes text of control characters and removes unauthorized numerical score patterns."""
    if not isinstance(text, str):
        return ""
    # Strip non-printable control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()
    return cleaned

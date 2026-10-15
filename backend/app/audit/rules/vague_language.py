import re
from typing import List, Pattern, Tuple

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule

# Curated regex patterns for absolutes and non-actionable subjective personality claims
ABSOLUTE_PATTERNS: List[Tuple[Pattern[str], str, str]] = [
    (
        re.compile(r"\b(always|never|constantly|every single time)\b", re.IGNORECASE),
        "absolute_quantifier",
        "medium",
    ),
    (
        re.compile(r"\b(bad attitude|unprofessional|lazy|incompetent|toxic|slacker)\b", re.IGNORECASE),
        "personality_pejorative",
        "high",
    ),
    (
        re.compile(r"\b(flawless|perfect|rockstar|ninja|10x)\b", re.IGNORECASE),
        "uncalibrated_hyperbole",
        "low",
    ),
    (
        re.compile(r"\b(difficult to work with|poor attitude|not a team player)\b", re.IGNORECASE),
        "subjective_non_behavioral",
        "medium",
    ),
]


class VagueLanguageRule(AuditRule):
    """
    Rule 4 — Vague and Absolute Claims Audit
    Detects absolute quantifiers ('always', 'never') and subjective personality judgments
    ('bad attitude', 'lazy') that lack specific, observable work-related evidence.
    Promotes concrete, behavioral, and evidence-grounded performance feedback.
    """

    @property
    def rule_name(self) -> str:
        return "vague_or_absolute_claims"

    @property
    def description(self) -> str:
        return "Flags absolute quantifiers and subjective personality descriptors that lack factual backing."

    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        flags: List[AuditFlagDraft] = []
        flagged_samples = set()

        # 1. Audit Feedback item contents
        for fb in context.feedback_items:
            content = fb.content or ""
            for pattern, category, severity in ABSOLUTE_PATTERNS:
                matches = pattern.findall(content)
                if matches:
                    matched_word = matches[0].lower()
                    sample_key = (fb.id, matched_word)
                    if sample_key not in flagged_samples:
                        flagged_samples.add(sample_key)
                        flags.append(
                            AuditFlagDraft(
                                flag_type=self.rule_name,
                                explanation=(
                                    f"Detected {category.replace('_', ' ')} '{matched_word}' in "
                                    f"{fb.feedback_type} feedback without accompanying measurable deliverable evidence."
                                ),
                                severity=severity,
                                evidence_ids=[],
                                suggested_action=(
                                    f"Replace absolute or personality descriptor '{matched_word}' with specific, "
                                    "observable engineering behaviors (e.g. pull request comments, ticket resolutions, or sprint metrics)."
                                ),
                            )
                        )

        # 2. Audit Findings statements
        for finding in context.findings:
            statement = finding.statement or ""
            for pattern, category, severity in ABSOLUTE_PATTERNS:
                matches = pattern.findall(statement)
                if matches:
                    matched_word = matches[0].lower()
                    sample_key = (finding.id, matched_word)
                    if sample_key not in flagged_samples:
                        flagged_samples.add(sample_key)
                        flags.append(
                            AuditFlagDraft(
                                flag_type=self.rule_name,
                                explanation=(
                                    f"Finding observation contains {category.replace('_', ' ')} '{matched_word}': "
                                    f"'{statement[:100]}...'"
                                ),
                                severity=severity,
                                evidence_ids=[],
                                suggested_action=(
                                    "Calibrate statement to describe concrete technical outcomes rather than broad absolute claims."
                                ),
                            )
                        )

        return flags

from datetime import timedelta
from typing import List

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule


class RecencyConcentrationRule(AuditRule):
    """
    Rule 2 — Recency Concentration Risk Audit
    Compares the chronological distribution of evidence and feedback against the review
    period timeline to flag reviews that disproportionately emphasize events from a narrow recent
    window while earlier review-period contributions are unexamined.
    """

    @property
    def rule_name(self) -> str:
        return "recency_concentration"

    @property
    def description(self) -> str:
        return "Detects when evidence is heavily concentrated in the final quartile of the review period."

    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        flags: List[AuditFlagDraft] = []

        period_start = context.cycle_start
        period_end = context.cycle_end
        total_cycle_days = (period_end - period_start).days

        # Only evaluate recency bias for review cycles with meaningful duration (>= 30 days)
        if total_cycle_days < 30:
            return flags

        # Extract dates from verified evidence items
        dated_evidence = [e for e in context.evidence_items if e.source_date is not None]
        if len(dated_evidence) < 2:
            return flags

        # Calculate the final 25% boundary date
        recency_window_days = max(7, int(total_cycle_days * 0.25))
        recency_cutoff = period_end - timedelta(days=recency_window_days)

        recent_items = [e for e in dated_evidence if e.source_date >= recency_cutoff]
        recent_ratio = len(recent_items) / len(dated_evidence)

        # Flag if 75% or more of dated evidence is compressed into the final quartile
        if recent_ratio >= 0.75 and len(dated_evidence) >= 3:
            recent_ids = [e.id for e in recent_items]
            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(
                        f"Potential recency concentration detected: {len(recent_items)} of {len(dated_evidence)} "
                        f"({int(recent_ratio * 100)}%) evidence records fall in the final {recency_window_days} days "
                        f"of the {total_cycle_days}-day review period ({period_start} to {period_end})."
                    ),
                    severity="medium",
                    evidence_ids=recent_ids,
                    suggested_action=(
                        "Verify whether earlier contributions from earlier quarters were examined, "
                        "and verify if significant deliverables from the first half of the cycle should be included."
                    ),
                )
            )

        return flags

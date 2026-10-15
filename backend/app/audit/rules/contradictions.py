import uuid
from typing import List

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule


class ContradictoryFeedbackRule(AuditRule):
    """
    Rule 5 — Contradictory Feedback & Divergent Signals Audit
    Identifies conflicting claims or divergent evaluative perspectives across peer, self,
    and manager reviews or AI findings, highlighting source references on both sides.
    """

    @property
    def rule_name(self) -> str:
        return "contradictory_feedback"

    @property
    def description(self) -> str:
        return "Identifies opposing or conflicting feedback signals across reviews and findings."

    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        flags: List[AuditFlagDraft] = []

        # 1. Audit explicit contradiction findings from Phase 5 analysis
        contradiction_findings = [f for f in context.findings if f.finding_type == "contradiction"]
        for cf in contradiction_findings:
            raw_eids = cf.evidence_ids or []
            parsed_eids = []
            for eid in raw_eids:
                try:
                    parsed_eids.append(uuid.UUID(str(eid)))
                except (ValueError, AttributeError):
                    pass

            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(f"Contradictory performance observation identified: {cf.statement[:160]}"),
                    severity="review",
                    evidence_ids=parsed_eids,
                    suggested_action=(
                        "Address the divergent signals during the review calibration sync. "
                        "Explore differing team contexts or project phases that explain the contrast."
                    ),
                )
            )

        # 2. Check for polarity clash in feedback submissions
        if len(context.feedback_items) >= 2:
            positive_signals = []
            critical_signals = []

            for fb in context.feedback_items:
                content_lower = (fb.content or "").lower()
                # Simple sentiment indicator checks
                has_pos = any(
                    word in content_lower
                    for word in ["exceptional", "exceeded", "outstanding", "masterful", "flawlessly"]
                )
                has_crit = any(
                    word in content_lower
                    for word in ["missed deadline", "blocked team", "slow", "struggled", "failed to deliver"]
                )
                if has_pos and not has_crit:
                    positive_signals.append(fb)
                elif has_crit and not has_pos:
                    critical_signals.append(fb)

            if positive_signals and critical_signals and not contradiction_findings:
                pos_sample = positive_signals[0]
                crit_sample = critical_signals[0]
                flags.append(
                    AuditFlagDraft(
                        flag_type=self.rule_name,
                        explanation=(
                            f"Identified contrasting sentiment across feedback submissions: "
                            f"{pos_sample.feedback_type} reviewer reported strong delivery while "
                            f"{crit_sample.feedback_type} reviewer reported delivery friction."
                        ),
                        severity="medium",
                        evidence_ids=[],
                        suggested_action=(
                            "Review both feedback perspectives side-by-side during calibration to understand "
                            "differing expectations between stakeholders."
                        ),
                    )
                )

        return flags

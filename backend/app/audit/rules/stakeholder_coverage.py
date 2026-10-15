from typing import List

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule


class StakeholderCoverageRule(AuditRule):
    """
    Rule 3 — Stakeholder Coverage Audit
    Evaluates the balance and diversity of feedback sources across self-assessment,
    peer perspectives, and manager feedback.
    Warns when expected perspectives are missing without penalizing the subject employee.
    """

    @property
    def rule_name(self) -> str:
        return "stakeholder_coverage"

    @property
    def description(self) -> str:
        return "Audits multi-stakeholder feedback diversity (self, peer, manager) to avoid single-perspective bias."

    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        flags: List[AuditFlagDraft] = []

        self_reviews = [fb for fb in context.feedback_items if fb.feedback_type == "self"]
        peer_reviews = [fb for fb in context.feedback_items if fb.feedback_type == "peer"]

        total_feedback = len(context.feedback_items)

        # 1. Check for missing self-assessment
        if len(self_reviews) == 0:
            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(
                        "Review cycle lacks a self-assessment submission from the subject employee. "
                        "The evaluation risks missing employee-identified context and accomplishments."
                    ),
                    severity="review",
                    evidence_ids=[],
                    suggested_action=(
                        "Encourage the employee to complete a self-review submission covering their "
                        "primary milestones, architectural challenges, and growth goals before review finalization."
                    ),
                )
            )

        # 2. Check for missing peer feedback
        if len(peer_reviews) == 0:
            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(
                        "Review cycle has 0 peer review submissions. "
                        "Observations lack 360-degree peer engineering collaboration signals."
                    ),
                    severity="review",
                    evidence_ids=[],
                    suggested_action=(
                        "Invite 1–2 peer engineers who collaborated on code reviews or technical projects to provide input. "
                        "(Note: In accordance with review governance, an absence of peer reviews must never be treated as negative performance)."
                    ),
                )
            )

        # 3. Check for single-source dominance
        if total_feedback >= 3:
            authors = {fb.author_id for fb in context.feedback_items if fb.author_id}
            if len(authors) == 1:
                flags.append(
                    AuditFlagDraft(
                        flag_type=self.rule_name,
                        explanation=(
                            f"Single-author feedback dominance: All {total_feedback} feedback submissions "
                            "originate from a single evaluator."
                        ),
                        severity="low",
                        evidence_ids=[],
                        suggested_action=(
                            "Collect feedback from additional collaborators to ensure a balanced, multi-perspective evaluation."
                        ),
                    )
                )

        return flags

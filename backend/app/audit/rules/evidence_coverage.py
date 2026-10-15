import uuid
from typing import List

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule


class EvidenceCoverageRule(AuditRule):
    """
    Rule 1 — Evidence Coverage Audit
    Identifies material performance claims, achievements, or draft findings that lack
    verifiable source evidence references or supporting examples.
    """

    @property
    def rule_name(self) -> str:
        return "evidence_coverage"

    @property
    def description(self) -> str:
        return "Flags material findings and achievements that lack verifiable evidence citations."

    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        flags: List[AuditFlagDraft] = []

        # 1. Check if cycle has completely zero evidence
        if len(context.evidence_items) == 0:
            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(
                        "Review cycle has zero verified evidence records attached. "
                        "All performance observations currently lack factual artifact grounding."
                    ),
                    severity="high",
                    evidence_ids=[],
                    suggested_action=(
                        "Gather and attach at least 2–3 primary work artifacts (pull requests, "
                        "design docs, incident postmortems, or tickets) before review finalization."
                    ),
                )
            )
            return flags

        # 2. Check individual findings for ungrounded citations or missing evidence
        unsupported_findings = [
            f
            for f in context.findings
            if not f.evidence_ids or len(f.evidence_ids) == 0 or f.validation_status == "unverified"
        ]

        if unsupported_findings:
            sample_statements = [f.statement[:80] for f in unsupported_findings[:3]]
            flags.append(
                AuditFlagDraft(
                    flag_type=self.rule_name,
                    explanation=(
                        f"Found {len(unsupported_findings)} finding(s) without verifiable source evidence "
                        f"citations (e.g. '{sample_statements[0]}...')."
                    ),
                    severity="review",
                    evidence_ids=[],
                    suggested_action=(
                        "Verify whether these claims correspond to specific engineering deliverables "
                        "and link the relevant evidence record IDs, or reframe them as discussion questions."
                    ),
                )
            )

        # 3. Check goals coverage
        if context.goals and len(context.evidence_items) > 0:
            valid_evidence_ids = {e.id for e in context.evidence_items}
            # Look at report draft structured content if available
            cited_in_draft = set()
            for r in context.reports:
                sc = r.structured_content or {}
                for s in sc.get("strengths", []):
                    for eid in s.get("supporting_evidence_ids", []):
                        try:
                            cited_in_draft.add(uuid.UUID(str(eid)))
                        except (ValueError, AttributeError):
                            pass

            # If draft cited fewer than half of available evidence
            if cited_in_draft and len(valid_evidence_ids) > 4 and len(cited_in_draft) < len(valid_evidence_ids) * 0.25:
                flags.append(
                    AuditFlagDraft(
                        flag_type=self.rule_name,
                        explanation=(
                            f"Review draft heavily concentrates on only {len(cited_in_draft)} of "
                            f"{len(valid_evidence_ids)} available verified evidence records."
                        ),
                        severity="low",
                        evidence_ids=list(cited_in_draft),
                        suggested_action=(
                            "Inspect whether unreferenced evidence items represent meaningful work "
                            "that should be factored into the final synthesis."
                        ),
                    )
                )

        return flags

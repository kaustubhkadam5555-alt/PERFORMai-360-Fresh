import logging
from typing import Dict, List, Optional, Tuple

from app.audit.base import AuditContext, AuditFlagDraft, AuditRule
from app.audit.rules.contradictions import ContradictoryFeedbackRule
from app.audit.rules.evidence_coverage import EvidenceCoverageRule
from app.audit.rules.recency_concentration import RecencyConcentrationRule
from app.audit.rules.stakeholder_coverage import StakeholderCoverageRule
from app.audit.rules.vague_language import VagueLanguageRule

logger = logging.getLogger(__name__)


class AuditEngine:
    """
    Deterministic Bias & Evidence-Quality Audit Engine.
    Executes the 5 core deterministic audit rules against a ReviewCycle context:
    1. Evidence Coverage
    2. Recency Concentration
    3. Stakeholder Coverage
    4. Vague or Absolute Language
    5. Contradictory Feedback
    """

    def __init__(self, custom_rules: Optional[List[AuditRule]] = None):
        self.rules: Dict[str, AuditRule] = {}
        registered = custom_rules or [
            EvidenceCoverageRule(),
            RecencyConcentrationRule(),
            StakeholderCoverageRule(),
            VagueLanguageRule(),
            ContradictoryFeedbackRule(),
        ]
        for r in registered:
            self.rules[r.rule_name] = r

    def run_audit(
        self,
        context: AuditContext,
        rules_to_run: Optional[List[str]] = None,
    ) -> Tuple[List[AuditFlagDraft], float, bool]:
        """
        Executes audit rules and calculates overall review health metrics.
        Returns: (flags, audit_health_score, is_ready_for_review)
        """
        active_rule_names = rules_to_run or list(self.rules.keys())
        all_flags: List[AuditFlagDraft] = []

        for name in active_rule_names:
            if name not in self.rules:
                logger.warning("Requested audit rule '%s' is not registered.", name)
                continue
            rule = self.rules[name]
            try:
                flags = rule.evaluate(context)
                all_flags.extend(flags)
            except Exception as exc:
                logger.exception("Error evaluating audit rule '%s': %s", name, exc)

        health_score = self.calculate_health_score(all_flags)
        is_ready = self.is_ready_for_review(all_flags)

        return all_flags, health_score, is_ready

    @staticmethod
    def calculate_health_score(flags: List[AuditFlagDraft]) -> float:
        """
        Computes a normalized review balance & quality score (0.0 to 1.0).
        Deductions are scaled by flag severity:
        - high severity: -0.20
        - medium severity: -0.10
        - review severity: -0.08
        - low severity: -0.03
        """
        score = 1.0
        deductions = {
            "high": 0.20,
            "medium": 0.10,
            "review": 0.08,
            "low": 0.03,
        }
        for f in flags:
            score -= deductions.get(f.severity.lower(), 0.08)

        return round(max(0.0, min(1.0, score)), 2)

    @staticmethod
    def is_ready_for_review(flags: List[AuditFlagDraft]) -> bool:
        """Indicates whether any critical (high severity) issues remain unaddressed."""
        has_high_severity = any(f.severity.lower() == "high" for f in flags)
        return not has_high_severity

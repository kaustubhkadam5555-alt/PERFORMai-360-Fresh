import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.finding import Finding
from app.models.goal import Goal
from app.models.review_cycle import ReviewCycle
from app.models.review_report import ReviewReport


@dataclass
class AuditFlagDraft:
    """Represents a generated audit flag candidate before persistence."""

    flag_type: str
    explanation: str
    severity: str = "review"  # "low", "medium", "high", "review"
    evidence_ids: List[uuid.UUID] = field(default_factory=list)
    suggested_action: Optional[str] = None


@dataclass
class AuditContext:
    """Contains all authorized domain artifacts scoped to a single review cycle."""

    cycle: ReviewCycle
    evidence_items: List[Evidence] = field(default_factory=list)
    feedback_items: List[Feedback] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    reports: List[ReviewReport] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)

    @property
    def cycle_start(self) -> date:
        return self.cycle.period_start

    @property
    def cycle_end(self) -> date:
        return self.cycle.period_end

    @property
    def total_evidence_count(self) -> int:
        return len(self.evidence_items)

    @property
    def total_feedback_count(self) -> int:
        return len(self.feedback_items)


class AuditRule(ABC):
    """Abstract base class for deterministic review-quality and bias audit rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique identifier of the rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief summary of the balance or evidence-quality condition audited."""
        pass

    @abstractmethod
    def evaluate(self, context: AuditContext) -> List[AuditFlagDraft]:
        """
        Evaluates the review context deterministically and returns zero or more AuditFlagDrafts.
        Must never raise exceptions; must fail safely and return an empty list or explicit limitation flag.
        """
        pass

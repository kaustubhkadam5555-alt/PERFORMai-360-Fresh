import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.bias_flag import BiasFlag
    from app.models.evidence import Evidence
    from app.models.feedback import Feedback
    from app.models.finding import Finding
    from app.models.goal import Goal
    from app.models.review_report import ReviewReport
    from app.models.team import Team
    from app.models.user import User
    from app.models.workflow_run import WorkflowRun


class ReviewCycleStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    OPEN = "open"
    COLLECTING_FEEDBACK = "collecting_feedback"
    IN_REVIEW = "in_review"
    ANALYSIS_PENDING = "analysis_pending"
    DRAFT_REPORT = "draft_report"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    COMPLETED = "completed"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class ReviewCycle(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_cycles"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ReviewCycleStatus.DRAFT.value, nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(100), default="standard_swe_v1", nullable=False)

    # Relationships
    employee: Mapped["User"] = relationship("User", back_populates="cycles_as_employee", foreign_keys=[employee_id])
    owner: Mapped["User"] = relationship("User", back_populates="cycles_as_owner", foreign_keys=[owner_id])
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="review_cycles", foreign_keys=[team_id])
    feedback_items: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="review_cycle", cascade="all, delete-orphan"
    )
    goals: Mapped[List["Goal"]] = relationship("Goal", back_populates="review_cycle", cascade="all, delete-orphan")
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="review_cycle", cascade="all, delete-orphan"
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding", back_populates="review_cycle", cascade="all, delete-orphan"
    )
    bias_flags: Mapped[List["BiasFlag"]] = relationship(
        "BiasFlag", back_populates="review_cycle", cascade="all, delete-orphan"
    )
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="review_cycle", cascade="all, delete-orphan"
    )
    reports: Mapped[List["ReviewReport"]] = relationship(
        "ReviewReport", back_populates="review_cycle", cascade="all, delete-orphan"
    )

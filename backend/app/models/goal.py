import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_cycle import ReviewCycle


class GoalStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ACHIEVED = "achieved"
    PARTIALLY_ACHIEVED = "partially_achieved"
    MISSED = "missed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Goal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "goals"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    measurable_target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=GoalStatus.IN_PROGRESS.value, nullable=False, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="goals")

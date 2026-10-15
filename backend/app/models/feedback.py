import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_cycle import ReviewCycle
    from app.models.user import User


class FeedbackType(str, enum.Enum):
    SELF = "self"
    PEER = "peer"
    MANAGER = "manager"


class FeedbackVisibility(str, enum.Enum):
    SHARED = "shared"
    MANAGER_ONLY = "manager_only"
    PRIVATE = "private"


class Feedback(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "feedbacks"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    feedback_type: Mapped[str] = mapped_column(String(50), default=FeedbackType.PEER.value, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(50), default=FeedbackVisibility.SHARED.value, nullable=False)

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="feedback_items")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="feedback_authored")
    subject_employee: Mapped["User"] = relationship(
        "User", foreign_keys=[subject_employee_id], back_populates="feedback_received"
    )

import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_cycle import ReviewCycle


class BiasFlag(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bias_flags"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="review", nullable=False)
    evidence_ids: Mapped[Optional[List[Any]]] = mapped_column(JSON, default=list, nullable=True)
    suggested_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="bias_flags")

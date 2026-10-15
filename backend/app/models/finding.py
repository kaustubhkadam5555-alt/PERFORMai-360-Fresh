import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_cycle import ReviewCycle


class Finding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "findings"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    origin_type: Mapped[str] = mapped_column(String(50), default="evidence_supported", nullable=False)
    evidence_ids: Mapped[Optional[List[Any]]] = mapped_column(JSON, default=list, nullable=True)
    limitations: Mapped[Optional[List[Any]]] = mapped_column(JSON, default=list, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(50), default="validated", nullable=False)

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="findings")

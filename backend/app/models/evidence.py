import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_cycle import ReviewCycle
    from app.models.user import User


class EvidenceSourceType(str, enum.Enum):
    DOCUMENT = "document"
    NOTE = "note"
    METRIC = "metric"
    TICKET = "ticket"
    COMMIT_SUMMARY = "commit_summary"


class EvidenceAccessPolicy(str, enum.Enum):
    INTERNAL = "internal"
    MANAGER_ONLY = "manager_only"
    RESTRICTED = "restricted"


class Evidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "evidence"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(50), default=EvidenceSourceType.DOCUMENT.value, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    uploader_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    access_policy: Mapped[str] = mapped_column(String(50), default=EvidenceAccessPolicy.INTERNAL.value, nullable=False)

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="evidence_items")
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="evidence_uploaded")

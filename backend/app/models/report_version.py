import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.review_cycle import ReviewCycle
    from app.models.review_report import ReviewReport
    from app.models.user import User


class ReportVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint("report_id", "version_number", name="uq_report_versions_report_id_version_number"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    structured_content: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)

    # Revision tracking metadata
    changed_section: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    author_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    report: Mapped["ReviewReport"] = relationship("ReviewReport", back_populates="versions")
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="version")

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.report_version import ReportVersion
    from app.models.review_report import ReviewReport
    from app.models.user import User


class Approval(Base, UUIDMixin):
    __tablename__ = "approvals"

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("report_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    report: Mapped["ReviewReport"] = relationship("ReviewReport", back_populates="approvals")
    version: Mapped[Optional["ReportVersion"]] = relationship("ReportVersion", back_populates="approvals")
    reviewer: Mapped["User"] = relationship("User", back_populates="approvals")

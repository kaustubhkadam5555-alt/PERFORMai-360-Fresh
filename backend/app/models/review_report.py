import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.report_version import ReportVersion
    from app.models.review_cycle import ReviewCycle
    from app.models.user import User
    from app.models.workflow_run import WorkflowRun


class ReviewReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_reports"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    structured_content: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    generated_by_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    review_cycle: Mapped["ReviewCycle"] = relationship("ReviewCycle", back_populates="reports")
    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun", back_populates="reports")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="report", cascade="all, delete-orphan"
    )
    versions: Mapped[List["ReportVersion"]] = relationship(
        "ReportVersion",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="desc(ReportVersion.version_number)",
    )

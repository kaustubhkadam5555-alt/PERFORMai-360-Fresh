import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.audit_event import AuditEvent
    from app.models.evidence import Evidence
    from app.models.feedback import Feedback
    from app.models.review_cycle import ReviewCycle
    from app.models.team import Team, TeamMembership


class UserRole(str, enum.Enum):
    EMPLOYEE = "employee"
    PEER_REVIEWER = "peer_reviewer"
    MANAGER = "manager"
    ADMINISTRATOR = "administrator"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.EMPLOYEE.value, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    teams_managed: Mapped[List["Team"]] = relationship("Team", back_populates="manager", foreign_keys="Team.manager_id")
    team_memberships: Mapped[List["TeamMembership"]] = relationship(
        "TeamMembership", back_populates="user", cascade="all, delete-orphan"
    )
    cycles_as_employee: Mapped[List["ReviewCycle"]] = relationship(
        "ReviewCycle", back_populates="employee", foreign_keys="ReviewCycle.employee_id"
    )
    cycles_as_owner: Mapped[List["ReviewCycle"]] = relationship(
        "ReviewCycle", back_populates="owner", foreign_keys="ReviewCycle.owner_id"
    )
    feedback_authored: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="author", foreign_keys="Feedback.author_id"
    )
    feedback_received: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="subject_employee", foreign_keys="Feedback.subject_employee_id"
    )
    evidence_uploaded: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="uploader", foreign_keys="Evidence.uploader_id"
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="actor", foreign_keys="AuditEvent.actor_id"
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="reviewer", foreign_keys="Approval.reviewer_id"
    )

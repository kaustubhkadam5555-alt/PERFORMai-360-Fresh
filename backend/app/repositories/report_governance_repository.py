import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.report_version import ReportVersion
from app.models.review_report import ReviewReport


class ReportGovernanceRepository:
    """Repository layer for report versions, approvals, and governance audit events."""

    # --- Report Queries & Updates ---

    @staticmethod
    async def get_report_by_id(
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> Optional[ReviewReport]:
        stmt = select(ReviewReport).where(ReviewReport.id == report_id).options(selectinload(ReviewReport.review_cycle))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_latest_report_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
    ) -> Optional[ReviewReport]:
        stmt = (
            select(ReviewReport)
            .where(ReviewReport.cycle_id == cycle_id)
            .order_by(desc(ReviewReport.version_number))
            .options(selectinload(ReviewReport.review_cycle))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def update_report(
        db: AsyncSession,
        report: ReviewReport,
    ) -> ReviewReport:
        await db.commit()
        await db.refresh(report)
        return report

    # --- ReportVersion Operations ---

    @staticmethod
    async def create_version(
        db: AsyncSession,
        report_id: uuid.UUID,
        cycle_id: uuid.UUID,
        version_number: int,
        structured_content: Dict[str, Any],
        status: str = "draft",
        changed_section: Optional[str] = None,
        change_summary: Optional[str] = None,
        author_id: Optional[uuid.UUID] = None,
        author_role: Optional[str] = None,
        is_ai_generated: bool = False,
    ) -> ReportVersion:
        version = ReportVersion(
            report_id=report_id,
            cycle_id=cycle_id,
            version_number=version_number,
            structured_content=structured_content,
            status=status,
            changed_section=changed_section,
            change_summary=change_summary,
            author_id=author_id,
            author_role=author_role,
            is_ai_generated=is_ai_generated,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version

    @staticmethod
    async def get_version_by_id(
        db: AsyncSession,
        version_id: uuid.UUID,
    ) -> Optional[ReportVersion]:
        stmt = select(ReportVersion).where(ReportVersion.id == version_id).options(selectinload(ReportVersion.author))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_version_by_number(
        db: AsyncSession,
        report_id: uuid.UUID,
        version_number: int,
    ) -> Optional[ReportVersion]:
        stmt = (
            select(ReportVersion)
            .where(
                ReportVersion.report_id == report_id,
                ReportVersion.version_number == version_number,
            )
            .options(selectinload(ReportVersion.author))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_versions_for_report(
        db: AsyncSession,
        report_id: uuid.UUID,
        limit: int = 50,
    ) -> List[ReportVersion]:
        stmt = (
            select(ReportVersion)
            .where(ReportVersion.report_id == report_id)
            .order_by(desc(ReportVersion.version_number))
            .options(selectinload(ReportVersion.author))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_latest_version(
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> Optional[ReportVersion]:
        stmt = (
            select(ReportVersion)
            .where(ReportVersion.report_id == report_id)
            .order_by(desc(ReportVersion.version_number))
            .options(selectinload(ReportVersion.author))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    # --- Approval Operations ---

    @staticmethod
    async def record_approval(
        db: AsyncSession,
        report_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: str,
        version_id: Optional[uuid.UUID] = None,
        version_number: Optional[int] = None,
        comments: Optional[str] = None,
    ) -> Approval:
        approval = Approval(
            report_id=report_id,
            reviewer_id=reviewer_id,
            version_id=version_id,
            version_number=version_number,
            decision=decision,
            comments=comments,
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval

    @staticmethod
    async def list_approvals_for_report(
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> List[Approval]:
        stmt = (
            select(Approval)
            .where(Approval.report_id == report_id)
            .order_by(desc(Approval.created_at))
            .options(selectinload(Approval.reviewer))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- AuditEvent Operations ---

    @staticmethod
    async def record_audit_event(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        actor_id: Optional[uuid.UUID] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            metadata_json=metadata_json or {},
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def list_audit_events_for_report(
        db: AsyncSession,
        report_id: uuid.UUID,
        limit: int = 100,
    ) -> List[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.resource_type == "review_report",
                AuditEvent.resource_id == str(report_id),
            )
            .order_by(desc(AuditEvent.created_at))
            .options(selectinload(AuditEvent.actor))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

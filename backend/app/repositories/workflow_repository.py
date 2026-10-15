import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.workflow_run import WorkflowRun


class WorkflowRepository:
    """Repository handling database operations for multi-agent workflows, approvals, and audit events."""

    @staticmethod
    async def create_workflow_run(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        workflow_status: str = "pending",
        current_stage: Optional[str] = "initialized",
        stage_state: Optional[Dict[str, Any]] = None,
        provider_metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            cycle_id=cycle_id,
            workflow_status=workflow_status,
            current_stage=current_stage,
            stage_state=stage_state or {},
            provider_metadata=provider_metadata or {},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    @staticmethod
    async def update_workflow_run(
        db: AsyncSession,
        run: WorkflowRun,
        workflow_status: Optional[str] = None,
        current_stage: Optional[str] = None,
        stage_state: Optional[Dict[str, Any]] = None,
        error_metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        if workflow_status is not None:
            run.workflow_status = workflow_status
        if current_stage is not None:
            run.current_stage = current_stage
        if stage_state is not None:
            run.stage_state = stage_state
        if error_metadata is not None:
            run.error_metadata = error_metadata
        await db.commit()
        await db.refresh(run)
        return run

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        run_id: uuid.UUID,
        include_reports: bool = True,
    ) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        if include_reports:
            stmt = stmt.options(selectinload(WorkflowRun.reports))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        limit: int = 50,
    ) -> List[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.cycle_id == cycle_id)
            .order_by(desc(WorkflowRun.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_latest_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
    ) -> Optional[WorkflowRun]:
        stmt = (
            select(WorkflowRun).where(WorkflowRun.cycle_id == cycle_id).order_by(desc(WorkflowRun.created_at)).limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_active_run_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
    ) -> Optional[WorkflowRun]:
        """Finds any currently running or awaiting_approval run for the cycle."""
        stmt = (
            select(WorkflowRun)
            .where(
                WorkflowRun.cycle_id == cycle_id,
                WorkflowRun.workflow_status.in_(["pending", "running", "awaiting_approval"]),
            )
            .order_by(desc(WorkflowRun.created_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    # --- Approval Persistence ---

    @staticmethod
    async def record_approval(
        db: AsyncSession,
        report_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: str,
        comments: Optional[str] = None,
    ) -> Approval:
        approval = Approval(
            report_id=report_id,
            reviewer_id=reviewer_id,
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
        stmt = select(Approval).where(Approval.report_id == report_id).order_by(desc(Approval.created_at))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- AuditEvent Persistence ---

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

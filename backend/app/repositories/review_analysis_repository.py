import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.review_report import ReviewReport
from app.models.workflow_run import WorkflowRun


class ReviewAnalysisRepository:
    """Repository handling database persistence for AI workflow runs, findings, and review reports."""

    # --- WorkflowRun ---

    @staticmethod
    async def create_workflow_run(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        workflow_status: str = "in_progress",
        current_stage: str = "evidence_analysis",
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
    async def get_workflow_run_by_id(
        db: AsyncSession,
        run_id: uuid.UUID,
    ) -> Optional[WorkflowRun]:
        result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
        return result.scalars().first()

    @staticmethod
    async def list_runs_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        limit: int = 50,
    ) -> List[WorkflowRun]:
        query = (
            select(WorkflowRun)
            .where(WorkflowRun.cycle_id == cycle_id)
            .order_by(desc(WorkflowRun.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    # --- Finding ---

    @staticmethod
    async def create_finding(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        finding_type: str,
        statement: str,
        origin_type: str = "evidence_supported",
        evidence_ids: Optional[List[Any]] = None,
        limitations: Optional[List[Any]] = None,
        validation_status: str = "validated",
    ) -> Finding:
        finding = Finding(
            cycle_id=cycle_id,
            finding_type=finding_type,
            statement=statement,
            origin_type=origin_type,
            evidence_ids=evidence_ids or [],
            limitations=limitations or [],
            validation_status=validation_status,
        )
        db.add(finding)
        await db.commit()
        await db.refresh(finding)
        return finding

    @staticmethod
    async def bulk_create_findings(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        findings_payloads: List[Dict[str, Any]],
    ) -> List[Finding]:
        findings: List[Finding] = []
        for p in findings_payloads:
            f = Finding(
                cycle_id=cycle_id,
                finding_type=p.get("finding_type", "observation"),
                statement=p.get("statement", ""),
                origin_type=p.get("origin_type", "evidence_supported"),
                evidence_ids=p.get("evidence_ids", []),
                limitations=p.get("limitations", []),
                validation_status=p.get("validation_status", "validated"),
            )
            db.add(f)
            findings.append(f)
        await db.commit()
        for f in findings:
            await db.refresh(f)
        return findings

    @staticmethod
    async def list_findings_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        finding_type: Optional[str] = None,
    ) -> List[Finding]:
        query = select(Finding).where(Finding.cycle_id == cycle_id)
        if finding_type:
            query = query.where(Finding.finding_type == finding_type)
        query = query.order_by(desc(Finding.created_at))
        result = await db.execute(query)
        return list(result.scalars().all())

    # --- ReviewReport ---

    @staticmethod
    async def create_or_update_report(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        structured_content: Dict[str, Any],
        generated_by_run_id: Optional[uuid.UUID] = None,
        created_by_id: Optional[uuid.UUID] = None,
        status: str = "draft",
    ) -> ReviewReport:
        # Check current latest version for cycle
        query = (
            select(ReviewReport).where(ReviewReport.cycle_id == cycle_id).order_by(desc(ReviewReport.version_number))
        )
        result = await db.execute(query)
        latest = result.scalars().first()
        next_version = (latest.version_number + 1) if latest else 1

        report = ReviewReport(
            cycle_id=cycle_id,
            version_number=next_version,
            structured_content=structured_content,
            status=status,
            generated_by_run_id=generated_by_run_id,
            created_by_id=created_by_id,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    @staticmethod
    async def get_latest_report_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
    ) -> Optional[ReviewReport]:
        query = (
            select(ReviewReport).where(ReviewReport.cycle_id == cycle_id).order_by(desc(ReviewReport.version_number))
        )
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_report_by_id(
        db: AsyncSession,
        report_id: uuid.UUID,
    ) -> Optional[ReviewReport]:
        result = await db.execute(select(ReviewReport).where(ReviewReport.id == report_id))
        return result.scalars().first()

import difflib
import logging
import uuid
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report_version import ReportVersion
from app.models.review_cycle import ReviewCycle
from app.models.review_report import ReviewReport
from app.repositories.report_governance_repository import ReportGovernanceRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.report_governance import (
    ApprovalHistoryResponse,
    ApprovalRecordResponse,
    GovernanceAuditEventResponse,
    GovernanceAuditListResponse,
    ReportApprovalRequest,
    ReportDetailResponse,
    ReportRevisionRequest,
    ReportVersionDetail,
    ReportVersionListResponse,
    ReportVersionSummary,
    SectionDiffResult,
    SectionEditRequest,
    VersionComparisonResponse,
)

logger = logging.getLogger(__name__)

SUPPORTED_SECTIONS: Set[str] = {
    "executive_summary",
    "strengths",
    "growth_areas",
    "goal_progress",
    "impact_highlights",
    "evidence_gaps_and_limitations",
    "suggested_discussion_questions",
    "reviewer_notes",
}


class ReportGovernanceService:
    """
    Comprehensive service for Phase 8 Report Governance:
    - Section-level editing with optimistic concurrency control
    - Immutable report version history and snapshotting
    - Deterministic version comparison and diff calculation
    - Version-bound human manager approval and sign-off
    - Tamper-resistant protection for approved versions
    - Traceable governance audit event logging
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------------------
    # Authorization & Scoping Helper
    # ---------------------------------------------------------------------------

    async def _verify_access(
        self,
        report: ReviewReport,
        viewer_id: Optional[uuid.UUID],
        viewer_role: Optional[str],
        require_manager: bool = False,
    ) -> None:
        """Enforces review-cycle and employee scoping. Rejects unauthorized access with HTTP 404 or 403."""
        role_lower = (viewer_role or "employee").lower()

        if require_manager and role_lower not in {"manager", "admin", "administrator"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{viewer_role}' is not authorized to perform report governance mutations.",
            )

        cycle: Optional[ReviewCycle] = report.review_cycle
        if not cycle:
            cycle = await ReviewCycleRepository.get_by_id(self.db, report.cycle_id)

        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated review cycle not found.",
            )

        # Cross-employee protection: An employee can only view their own report
        if role_lower == "employee":
            if not viewer_id or cycle.employee_id != viewer_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Report '{report.id}' not found.",
                )

        # Manager scoping: A manager cannot approve or edit their own review
        if role_lower == "manager" and viewer_id:
            if cycle.employee_id == viewer_id and require_manager:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Employees cannot approve or edit their own performance reviews.",
                )

    # ---------------------------------------------------------------------------
    # Report Retrieval
    # ---------------------------------------------------------------------------

    async def get_report_by_id(
        self,
        report_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReportDetailResponse:
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)
        return await self._build_report_detail(report, viewer_role=viewer_role)

    async def get_report_for_cycle(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReportDetailResponse:
        report = await ReportGovernanceRepository.get_latest_report_for_cycle(self.db, cycle_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No report found for review cycle '{cycle_id}'.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)
        return await self._build_report_detail(report, viewer_role=viewer_role)

    # ---------------------------------------------------------------------------
    # Feature A: Section-Level Report Editing
    # ---------------------------------------------------------------------------

    async def edit_section(
        self,
        report_id: uuid.UUID,
        section_key: str,
        request_in: SectionEditRequest,
        editor_id: Optional[uuid.UUID] = None,
        editor_role: Optional[str] = None,
    ) -> ReportDetailResponse:
        """
        Edits an individual report section transactionally:
        - Validates section key and content constraints.
        - Enforces optimistic concurrency (rejects stale base versions with 409).
        - Protects previously approved versions (approved versions are frozen; new draft version is spawned).
        - Creates an immutable ReportVersion snapshot.
        - Logs an AuditEvent for traceability.
        """
        if request_in.base_version_number <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="base_version_number must be greater than 0",
            )

        if section_key not in SUPPORTED_SECTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid section '{section_key}'. Supported sections: {sorted(list(SUPPORTED_SECTIONS))}",
            )

        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, editor_id, editor_role, require_manager=True)

        # 1. Optimistic Concurrency Control
        if request_in.base_version_number != report.version_number:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Version conflict: The report is currently at version {report.version_number}, "
                    f"but your edit was based on version {request_in.base_version_number}. "
                    "Please reload the report to review the latest changes before saving."
                ),
            )

        # 2. Content Validation & Sanitization
        validated_content = self._validate_and_sanitize_section(section_key, request_in.content)

        # 3. Clone and update structured content dictionary
        current_content = dict(report.structured_content or {})
        current_content[section_key] = validated_content

        # Update citations list if strengths or growth areas were edited
        if section_key in {"strengths", "growth_areas"}:
            citations_set = set()
            for s in current_content.get("strengths", []):
                for cid in s.get("supporting_evidence_ids", []):
                    citations_set.add(str(cid))
            for g in current_content.get("growth_areas", []):
                for cid in g.get("supporting_evidence_ids", []):
                    citations_set.add(str(cid))
            current_content["citations"] = sorted(list(citations_set))

        # 4. Version Increment and Approved Snapshot Protection
        next_version = report.version_number + 1

        # If previous version was approved, it remains frozen as approved; the new version is draft
        report.version_number = next_version
        report.structured_content = current_content
        report.status = "draft"
        await self.db.commit()
        await self.db.refresh(report)

        # 5. Create immutable ReportVersion snapshot
        change_summary = request_in.reason or f"Edited section '{section_key}'"
        version = await ReportGovernanceRepository.create_version(
            db=self.db,
            report_id=report.id,
            cycle_id=report.cycle_id,
            version_number=next_version,
            structured_content=current_content,
            status="draft",
            changed_section=section_key,
            change_summary=change_summary,
            author_id=editor_id,
            author_role=editor_role or "manager",
            is_ai_generated=False,
        )

        # 6. Audit Trail Logging
        await ReportGovernanceRepository.record_audit_event(
            db=self.db,
            action="report.section_edited",
            resource_type="review_report",
            resource_id=str(report.id),
            actor_id=editor_id,
            metadata_json={
                "section": section_key,
                "version_number": next_version,
                "version_id": str(version.id),
                "reason": request_in.reason,
                "author_role": editor_role,
            },
        )

        logger.info(
            "Report %s section '%s' edited by %s (version %s -> %s)",
            report.id,
            section_key,
            editor_id,
            request_in.base_version_number,
            next_version,
        )
        return await self._build_report_detail(report, viewer_role=editor_role)

    # ---------------------------------------------------------------------------
    # Feature B: Version Listing & History
    # ---------------------------------------------------------------------------

    async def list_versions(
        self,
        report_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        limit: int = 50,
    ) -> ReportVersionListResponse:
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)
        versions = await ReportGovernanceRepository.list_versions_for_report(self.db, report_id, limit=limit)

        summaries = [
            ReportVersionSummary(
                version_id=v.id,
                report_id=v.report_id,
                cycle_id=v.cycle_id,
                version_number=v.version_number,
                status=v.status,
                changed_section=v.changed_section,
                change_summary=v.change_summary,
                author_id=v.author_id,
                author_role=v.author_role,
                is_ai_generated=v.is_ai_generated,
                created_at=v.created_at,
            )
            for v in versions
        ]

        return ReportVersionListResponse(
            report_id=report.id,
            cycle_id=report.cycle_id,
            current_version_number=report.version_number,
            total_versions=len(summaries),
            versions=summaries,
        )

    async def get_version(
        self,
        report_id: uuid.UUID,
        version_identifier: str,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ReportVersionDetail:
        """Retrieves exact snapshot of a version by UUID or version number."""
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)

        # Check if version_identifier is an integer version number or UUID
        try:
            v_num = int(version_identifier)
            if v_num <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Version numbers must be greater than 0.",
                )
        except ValueError:
            pass

        version: Optional[ReportVersion] = None
        if version_identifier.isdigit():
            version = await ReportGovernanceRepository.get_version_by_number(
                self.db, report_id, int(version_identifier)
            )
        else:
            try:
                v_uuid = uuid.UUID(version_identifier)
                version = await ReportGovernanceRepository.get_version_by_id(self.db, v_uuid)
            except ValueError:
                version = None

        if not version or version.report_id != report_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version '{version_identifier}' not found for report '{report_id}'.",
            )

        raw_content = version.structured_content or {}
        if viewer_role and viewer_role.lower() == "employee":
            structured_content = {k: v for k, v in raw_content.items() if k != "reviewer_notes"}
        else:
            structured_content = raw_content

        return ReportVersionDetail(
            version_id=version.id,
            report_id=version.report_id,
            cycle_id=version.cycle_id,
            version_number=version.version_number,
            status=version.status,
            changed_section=version.changed_section,
            change_summary=version.change_summary,
            author_id=version.author_id,
            author_role=version.author_role,
            is_ai_generated=version.is_ai_generated,
            created_at=version.created_at,
            structured_content=structured_content,
        )

    # ---------------------------------------------------------------------------
    # Feature C: Version Comparison
    # ---------------------------------------------------------------------------

    async def compare_versions(
        self,
        report_id: uuid.UUID,
        from_version_identifier: str,
        to_version_identifier: str,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> VersionComparisonResponse:
        """
        Computes a deterministic, transparent comparison between two versions of the same report:
        - Added, removed, and modified sections.
        - Unified text diffs for prose.
        - Additions and deletions for list sections and citations.
        - Governance status changes.
        """
        try:
            if int(from_version_identifier) <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Version numbers must be greater than 0",
                )
        except ValueError:
            pass

        try:
            if int(to_version_identifier) <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Version numbers must be greater than 0",
                )
        except ValueError:
            pass

        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)

        v_from = await self._resolve_version(report_id, from_version_identifier)
        v_to = await self._resolve_version(report_id, to_version_identifier)

        # Verify both belong to the exact same report
        if v_from.report_id != report_id or v_to.report_id != report_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both versions must belong to the same review report.",
            )

        content_from = v_from.structured_content or {}
        content_to = v_to.structured_content or {}

        sections_changed: List[str] = []
        section_diffs: Dict[str, SectionDiffResult] = {}
        change_summary_bullets: List[str] = []

        all_keys = sorted(list(set(content_from.keys()) | set(content_to.keys())))

        for key in all_keys:
            val_from = content_from.get(key)
            val_to = content_to.get(key)

            if val_from == val_to:
                continue

            sections_changed.append(key)

            if isinstance(val_from, str) or isinstance(val_to, str):
                str_from = str(val_from or "")
                str_to = str(val_to or "")
                diff_lines = list(
                    difflib.unified_diff(
                        str_from.splitlines(keepends=True),
                        str_to.splitlines(keepends=True),
                        fromfile=f"v{v_from.version_number}:{key}",
                        tofile=f"v{v_to.version_number}:{key}",
                    )
                )
                section_diffs[key] = SectionDiffResult(
                    section_key=key,
                    is_modified=True,
                    diff_type="text",
                    previous_value=str_from,
                    current_value=str_to,
                    unified_diff="".join(diff_lines),
                )
                change_summary_bullets.append(f"Modified text in '{key}'")

            elif isinstance(val_from, list) or isinstance(val_to, list):
                list_from = list(val_from or [])
                list_to = list(val_to or [])

                added = [item for item in list_to if item not in list_from]
                removed = [item for item in list_from if item not in list_to]

                section_diffs[key] = SectionDiffResult(
                    section_key=key,
                    is_modified=True,
                    diff_type="list",
                    previous_value=list_from,
                    current_value=list_to,
                    added_items=added,
                    removed_items=removed,
                )
                change_summary_bullets.append(f"Updated '{key}': +{len(added)} added, -{len(removed)} removed")

            else:
                section_diffs[key] = SectionDiffResult(
                    section_key=key,
                    is_modified=True,
                    diff_type="object",
                    previous_value=val_from,
                    current_value=val_to,
                )
                change_summary_bullets.append(f"Updated structured content for '{key}'")

        # Citations changes
        citations_from = set(content_from.get("citations", []))
        citations_to = set(content_to.get("citations", []))
        added_citations = sorted(list(citations_to - citations_from))
        removed_citations = sorted(list(citations_from - citations_to))

        if added_citations:
            change_summary_bullets.append(f"Added citations: {', '.join(added_citations)}")
        if removed_citations:
            change_summary_bullets.append(f"Removed citations: {', '.join(removed_citations)}")

        # Status change note
        if v_from.status != v_to.status:
            change_summary_bullets.append(f"Status transition: {v_from.status} -> {v_to.status}")

        if viewer_role and viewer_role.lower() == "employee":
            section_diffs = {k: v for k, v in section_diffs.items() if k != "reviewer_notes"}
            sections_changed = [s for s in sections_changed if s != "reviewer_notes"]
            change_summary_bullets = [s for s in change_summary_bullets if "reviewer_notes" not in s.lower()]

        return VersionComparisonResponse(
            report_id=report.id,
            cycle_id=report.cycle_id,
            from_version_number=v_from.version_number,
            to_version_number=v_to.version_number,
            from_version_id=v_from.id,
            to_version_id=v_to.id,
            from_status=v_from.status,
            to_status=v_to.status,
            from_author_role=v_from.author_role,
            to_author_role=v_to.author_role,
            from_created_at=v_from.created_at,
            to_created_at=v_to.created_at,
            sections_changed=sections_changed,
            section_diffs=section_diffs,
            added_citations=added_citations,
            removed_citations=removed_citations,
            change_summary=change_summary_bullets,
        )

    # ---------------------------------------------------------------------------
    # Feature D & E: Version-Bound Human Approval & Revision Requests
    # ---------------------------------------------------------------------------

    async def approve_report(
        self,
        report_id: uuid.UUID,
        request_in: ReportApprovalRequest,
        reviewer_id: uuid.UUID,
        reviewer_role: str,
    ) -> ReportDetailResponse:
        """
        Records human approval bound to an exact version:
        - Verifies reviewer role is manager or admin.
        - Enforces stale approval defense (version number/ID must match current version).
        - Idempotency: Rejects duplicate approvals for already-approved version.
        - Transactionally records Approval record and AuditEvent.
        - Syncs active WorkflowRun state to completed.
        """
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, reviewer_id, reviewer_role, require_manager=True)

        # Stale approval defense
        if request_in.version_number is not None and request_in.version_number != report.version_number:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Stale approval rejected: You inspected version {request_in.version_number}, "
                    f"but the report has advanced to version {report.version_number}. "
                    "Please review the latest version before submitting approval."
                ),
            )

        latest_version = await ReportGovernanceRepository.get_latest_version(self.db, report.id)
        if not latest_version:
            # Create snapshot for version 1 if not present
            latest_version = await ReportGovernanceRepository.create_version(
                db=self.db,
                report_id=report.id,
                cycle_id=report.cycle_id,
                version_number=report.version_number,
                structured_content=report.structured_content,
                status=report.status,
                changed_section="all",
                change_summary="Initial report snapshot",
                author_id=reviewer_id,
                author_role=reviewer_role,
            )

        if request_in.version_id is not None and request_in.version_id != latest_version.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stale version ID '{request_in.version_id}'. The current version ID is '{latest_version.id}'.",
            )

        # Idempotency check: duplicate approval
        if report.status == "approved" and latest_version.status == "approved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Report version {report.version_number} is already approved and finalized.",
            )

        # Transactional state update
        report.status = "approved"
        latest_version.status = "approved"
        await self.db.commit()
        await self.db.refresh(report)
        await self.db.refresh(latest_version)

        # Record Approval
        approval = await ReportGovernanceRepository.record_approval(
            db=self.db,
            report_id=report.id,
            reviewer_id=reviewer_id,
            decision="approved",
            version_id=latest_version.id,
            version_number=report.version_number,
            comments=request_in.comments,
        )

        # Record AuditEvent
        await ReportGovernanceRepository.record_audit_event(
            db=self.db,
            action="report.approved",
            resource_type="review_report",
            resource_id=str(report.id),
            actor_id=reviewer_id,
            metadata_json={
                "approval_id": str(approval.id),
                "version_number": report.version_number,
                "version_id": str(latest_version.id),
                "reviewer_role": reviewer_role,
                "comments": request_in.comments,
            },
        )

        # Sync active WorkflowRun if present
        active_run = await WorkflowRepository.get_active_run_for_cycle(self.db, report.cycle_id)
        if active_run:
            active_run.workflow_status = "completed"
            active_run.current_stage = "completed"
            await self.db.commit()

        logger.info(
            "Report %s version %s approved by reviewer %s (%s)",
            report.id,
            report.version_number,
            reviewer_id,
            reviewer_role,
        )
        return await self._build_report_detail(report, viewer_role=reviewer_role)

    async def request_revision(
        self,
        report_id: uuid.UUID,
        request_in: ReportRevisionRequest,
        reviewer_id: uuid.UUID,
        reviewer_role: str,
    ) -> ReportDetailResponse:
        """
        Records reviewer revision instructions and transitions report to 'revision_requested':
        - Requires mandatory reviewer instructions.
        - Updates report and current version status.
        - Records an immutable Approval entry (decision="revision_requested").
        - Emits an AuditEvent.
        """
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, reviewer_id, reviewer_role, require_manager=True)

        if not request_in.comments or not request_in.comments.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Revision comments and instructions are mandatory when requesting revisions.",
            )

        latest_version = await ReportGovernanceRepository.get_latest_version(self.db, report.id)
        if not latest_version:
            latest_version = await ReportGovernanceRepository.create_version(
                db=self.db,
                report_id=report.id,
                cycle_id=report.cycle_id,
                version_number=report.version_number,
                structured_content=report.structured_content,
                status=report.status,
                changed_section="all",
                change_summary="Initial report snapshot",
                author_id=reviewer_id,
                author_role=reviewer_role,
            )

        report.status = "revision_requested"
        latest_version.status = "revision_requested"
        await self.db.commit()
        await self.db.refresh(report)
        await self.db.refresh(latest_version)

        approval = await ReportGovernanceRepository.record_approval(
            db=self.db,
            report_id=report.id,
            reviewer_id=reviewer_id,
            decision="revision_requested",
            version_id=latest_version.id,
            version_number=report.version_number,
            comments=request_in.comments,
        )

        await ReportGovernanceRepository.record_audit_event(
            db=self.db,
            action="report.revision_requested",
            resource_type="review_report",
            resource_id=str(report.id),
            actor_id=reviewer_id,
            metadata_json={
                "approval_id": str(approval.id),
                "version_number": report.version_number,
                "version_id": str(latest_version.id),
                "reviewer_role": reviewer_role,
                "instructions": request_in.comments,
            },
        )

        # Sync active WorkflowRun
        active_run = await WorkflowRepository.get_active_run_for_cycle(self.db, report.cycle_id)
        if active_run:
            active_run.workflow_status = "revision_requested"
            active_run.current_stage = "revision_handling"
            await self.db.commit()

        logger.info(
            "Report %s version %s revision requested by %s",
            report.id,
            report.version_number,
            reviewer_id,
        )
        return await self._build_report_detail(report, viewer_role=reviewer_role)

    # ---------------------------------------------------------------------------
    # Feature F: Approval History & Governance Audit Trail
    # ---------------------------------------------------------------------------

    async def get_approval_history(
        self,
        report_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> ApprovalHistoryResponse:
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)
        approvals = await ReportGovernanceRepository.list_approvals_for_report(self.db, report_id)

        records = [
            ApprovalRecordResponse(
                id=a.id,
                report_id=a.report_id,
                version_id=a.version_id,
                version_number=a.version_number,
                reviewer_id=a.reviewer_id,
                reviewer_name=a.reviewer.full_name if a.reviewer else None,
                reviewer_role=a.reviewer.role.value if a.reviewer and hasattr(a.reviewer.role, "value") else None,
                decision=a.decision,
                comments=a.comments,
                created_at=a.created_at,
            )
            for a in approvals
        ]

        return ApprovalHistoryResponse(
            report_id=report.id,
            cycle_id=report.cycle_id,
            total_records=len(records),
            approvals=records,
        )

    async def get_audit_history(
        self,
        report_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        limit: int = 100,
    ) -> GovernanceAuditListResponse:
        report = await ReportGovernanceRepository.get_report_by_id(self.db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )

        await self._verify_access(report, viewer_id, viewer_role, require_manager=False)
        events = await ReportGovernanceRepository.list_audit_events_for_report(self.db, report_id, limit=limit)

        records = [
            GovernanceAuditEventResponse(
                id=e.id,
                action=e.action,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                actor_id=e.actor_id,
                actor_name=e.actor.full_name if e.actor else None,
                actor_role=e.actor.role.value if e.actor and hasattr(e.actor.role, "value") else None,
                metadata_json=e.metadata_json or {},
                created_at=e.created_at,
            )
            for e in events
        ]

        return GovernanceAuditListResponse(
            report_id=report.id,
            cycle_id=report.cycle_id,
            total_events=len(records),
            events=records,
        )

    # ---------------------------------------------------------------------------
    # Private Helpers
    # ---------------------------------------------------------------------------

    async def _resolve_version(
        self,
        report_id: uuid.UUID,
        version_identifier: str,
    ) -> ReportVersion:
        version: Optional[ReportVersion] = None
        if version_identifier.isdigit():
            version = await ReportGovernanceRepository.get_version_by_number(
                self.db, report_id, int(version_identifier)
            )
        else:
            try:
                v_uuid = uuid.UUID(version_identifier)
                version = await ReportGovernanceRepository.get_version_by_id(self.db, v_uuid)
            except ValueError:
                version = None

        if not version or version.report_id != report_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version '{version_identifier}' not found for report '{report_id}'.",
            )
        return version

    def _validate_and_sanitize_section(self, section_key: str, content: Any) -> Any:
        """Validates section data shape, bounds, and content safety."""
        if section_key in {"executive_summary", "reviewer_notes"}:
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Section '{section_key}' content must be a text string.",
                )
            max_len = 10000 if section_key == "executive_summary" else 5000
            if len(content) > max_len:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Section '{section_key}' exceeds maximum permitted length of {max_len} characters.",
                )
            return content.strip()

        if section_key in {"strengths", "growth_areas", "goal_progress", "impact_highlights"}:
            if not isinstance(content, list):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Section '{section_key}' must be a list of items.",
                )
            # Ensure items are dictionaries and tag them with is_human_edited
            sanitized_items = []
            for item in content:
                if not isinstance(item, dict):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Each item in '{section_key}' must be a structured dictionary.",
                    )
                item_copy = dict(item)
                item_copy["is_human_edited"] = True
                sanitized_items.append(item_copy)
            return sanitized_items

        if section_key in {"evidence_gaps_and_limitations", "suggested_discussion_questions"}:
            if not isinstance(content, list):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Section '{section_key}' must be a list.",
                )
            return content

        return content

    async def _build_report_detail(
        self, report: ReviewReport, viewer_role: Optional[str] = None
    ) -> ReportDetailResponse:
        cycle: Optional[ReviewCycle] = report.review_cycle
        if not cycle:
            cycle = await ReviewCycleRepository.get_by_id(self.db, report.cycle_id)

        latest_version = await ReportGovernanceRepository.get_latest_version(self.db, report.id)
        approvals = await ReportGovernanceRepository.list_approvals_for_report(self.db, report.id)

        last_approval = next((a for a in approvals if a.decision == "approved"), None)
        last_edit = latest_version if latest_version and not latest_version.is_ai_generated else None

        raw_content = report.structured_content or {}
        if viewer_role and viewer_role.lower() == "employee":
            structured_content = {k: v for k, v in raw_content.items() if k != "reviewer_notes"}
        else:
            structured_content = raw_content

        return ReportDetailResponse(
            report_id=report.id,
            cycle_id=report.cycle_id,
            employee_id=cycle.employee_id if cycle else report.cycle_id,
            version_number=report.version_number,
            status=report.status,
            structured_content=structured_content,
            latest_version_id=latest_version.id if latest_version else None,
            is_approved=report.status == "approved",
            approved_version_number=last_approval.version_number if last_approval else None,
            last_approved_at=last_approval.created_at if last_approval else None,
            last_edited_by=last_edit.author_role if last_edit else None,
            last_edited_at=last_edit.created_at if last_edit else None,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

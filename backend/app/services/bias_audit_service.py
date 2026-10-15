import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.base import AuditContext, AuditFlagDraft
from app.audit.engine import AuditEngine
from app.models.review_cycle import ReviewCycle
from app.repositories.bias_flag_repository import BiasFlagRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.review_analysis_repository import ReviewAnalysisRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.schemas.bias_flag import (
    AuditExecutionRequest,
    AuditSummaryResponse,
    BiasFlagResponse,
    BiasFlagUpdate,
)

logger = logging.getLogger(__name__)


class BiasAuditService:
    """
    Service layer coordinating bias and review-quality auditing:
    1. Authorized review cycle scoping and RBAC enforcement
    2. Multi-source domain artifact aggregation (evidence, feedback, goals, findings)
    3. Deterministic rule evaluation via AuditEngine
    4. BiasFlag persistence, lifecycle state transitions, and audit summary metrics
    """

    def __init__(self, db: AsyncSession, engine: Optional[AuditEngine] = None):
        self.db = db
        self.engine = engine or AuditEngine()

    async def _verify_cycle_and_permissions(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        action: str = "view",
    ) -> ReviewCycle:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        # Administrators always have access
        if viewer_role in {"admin", "administrator"}:
            return cycle

        # Managers have access to execute audits and manage flags
        if viewer_role == "manager":
            return cycle

        if viewer_id is not None:
            # Cycle owner (manager / reviewer)
            if cycle.owner_id == viewer_id:
                return cycle
            # Subject employee: Can view audit summary and flags, but cannot mutate flag status
            if cycle.employee_id == viewer_id:
                if action == "mutate":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only managers, cycle owners, or administrators may calibrate or resolve audit flags",
                    )
                return cycle

            # Unrelated employee
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have authorization to view or audit this review cycle",
            )

        return cycle

    async def execute_audit(
        self,
        cycle_id: uuid.UUID,
        request_in: Optional[AuditExecutionRequest] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> AuditSummaryResponse:
        """
        Gathers review cycle domain artifacts, evaluates deterministic audit rules,
        stores newly generated flags, and returns an audit summary.
        """
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="view"
        )
        req = request_in or AuditExecutionRequest()

        # 1. Gather all cycle domain artifacts
        evidence_items = await EvidenceRepository.list_all_for_cycle(self.db, cycle.id)
        feedback_items = await FeedbackRepository.list_feedback(self.db, cycle_id=cycle.id, limit=200)
        findings = await ReviewAnalysisRepository.list_findings_for_cycle(self.db, cycle_id=cycle.id)
        latest_report = await ReviewAnalysisRepository.get_latest_report_for_cycle(self.db, cycle.id)
        reports = [latest_report] if latest_report else []
        goals = await GoalRepository.list_goals(self.db, cycle_id=cycle.id, limit=200)

        context = AuditContext(
            cycle=cycle,
            evidence_items=evidence_items,
            feedback_items=feedback_items,
            findings=findings,
            reports=reports,
            goals=goals,
        )

        # 2. Optionally clear open flags before re-evaluation, preserving human-calibrated flags
        if req.re_evaluate_all:
            await BiasFlagRepository.clear_open_flags_for_cycle(self.db, cycle.id, flag_types=req.rules_to_run)

        # 3. Execute deterministic audit rules
        draft_flags: List[AuditFlagDraft]
        draft_flags, _engine_score, _is_ready = self.engine.run_audit(
            context=context,
            rules_to_run=req.rules_to_run,
        )

        # 4. Check for existing flags to prevent duplicate open flags for the same explanation
        existing_flags = await BiasFlagRepository.list_for_cycle(self.db, cycle.id)
        existing_signatures = {(f.flag_type, f.explanation) for f in existing_flags}

        new_flags_payload: List[Dict[str, Any]] = []
        for draft in draft_flags:
            sig = (draft.flag_type, draft.explanation)
            if sig not in existing_signatures:
                new_flags_payload.append(
                    {
                        "flag_type": draft.flag_type,
                        "explanation": draft.explanation,
                        "severity": draft.severity,
                        "evidence_ids": [str(eid) for eid in draft.evidence_ids],
                        "suggested_action": draft.suggested_action,
                        "status": "open",
                        "reviewer_comment": None,
                    }
                )
                existing_signatures.add(sig)

        if new_flags_payload:
            await BiasFlagRepository.bulk_create(self.db, cycle.id, new_flags_payload)

        # 5. Return updated comprehensive audit summary
        return await self.get_audit_summary(cycle.id, viewer_id=viewer_id, viewer_role=viewer_role)

    async def get_audit_summary(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> AuditSummaryResponse:
        """Computes current aggregate audit health, status distribution, and flag listing."""
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="view"
        )
        flags = await BiasFlagRepository.list_for_cycle(self.db, cycle.id)

        open_flags = [f for f in flags if f.status == "open"]
        ack_flags = [f for f in flags if f.status == "acknowledged"]
        res_flags = [f for f in flags if f.status == "resolved"]
        na_flags = [f for f in flags if f.status == "not_applicable"]

        severity_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for f in flags:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            type_counts[f.flag_type] = type_counts.get(f.flag_type, 0) + 1

        # Calculate health score: Resolved and N/A flags are treated as calibrated and clear
        # Open flags incur full deduction; Acknowledged flags incur half deduction (under active calibration)
        score = 1.0
        deductions = {"high": 0.20, "medium": 0.10, "review": 0.08, "low": 0.03}
        for f in open_flags:
            score -= deductions.get(f.severity.lower(), 0.08)
        for f in ack_flags:
            score -= deductions.get(f.severity.lower(), 0.08) * 0.5

        health_score = round(max(0.0, min(1.0, score)), 2)

        # Ready for final managerial review if zero open high-severity flags remain
        is_ready = not any(f.severity.lower() == "high" for f in open_flags)

        flag_responses = [BiasFlagResponse.model_validate(f) for f in flags]

        return AuditSummaryResponse(
            cycle_id=cycle.id,
            total_flags=len(flags),
            open_flags=len(open_flags),
            acknowledged_flags=len(ack_flags),
            resolved_flags=len(res_flags),
            not_applicable_flags=len(na_flags),
            severity_breakdown=severity_counts,
            flag_type_breakdown=type_counts,
            audit_health_score=health_score,
            is_ready_for_review=is_ready,
            flags=flag_responses,
        )

    async def list_flags(
        self,
        cycle_id: uuid.UUID,
        status_filter: Optional[str] = None,
        flag_type_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> List[BiasFlagResponse]:
        """Lists audit flags for a cycle with optional filters and authorization enforcement."""
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="view"
        )
        flags = await BiasFlagRepository.list_for_cycle(
            self.db,
            cycle_id=cycle.id,
            status=status_filter,
            flag_type=flag_type_filter,
            severity=severity_filter,
        )
        return [BiasFlagResponse.model_validate(f) for f in flags]

    async def update_flag(
        self,
        cycle_id: uuid.UUID,
        flag_id: uuid.UUID,
        flag_update: BiasFlagUpdate,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> BiasFlagResponse:
        """
        Updates flag status (e.g. acknowledged, resolved, not_applicable) and records reviewer calibration notes.
        Enforces cross-cycle containment and manager/admin authorization.
        """
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="mutate"
        )

        flag = await BiasFlagRepository.get_by_id(self.db, flag_id)
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit flag with ID '{flag_id}' not found",
            )

        # Enforce cross-cycle containment
        if flag.cycle_id != cycle.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit flag with ID '{flag_id}' does not belong to review cycle '{cycle_id}'",
            )

        # Validate status if provided
        if flag_update.status:
            valid_statuses = {"open", "acknowledged", "resolved", "not_applicable"}
            if flag_update.status.lower() not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid status '{flag_update.status}'. Allowed: {', '.join(sorted(valid_statuses))}",
                )

        updated_flag = await BiasFlagRepository.update(self.db, flag, flag_update)
        return BiasFlagResponse.model_validate(updated_flag)

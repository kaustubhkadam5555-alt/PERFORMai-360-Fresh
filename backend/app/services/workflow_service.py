import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMProvider
from app.ai.provider import get_llm_provider
from app.models.review_cycle import ReviewCycle
from app.models.workflow_run import WorkflowRun
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.workflow import (
    WorkflowApprovalRequest,
    WorkflowCancelRequest,
    WorkflowDraftReport,
    WorkflowListResponse,
    WorkflowRevisionRequest,
    WorkflowStageStatus,
    WorkflowStartRequest,
    WorkflowStatusResponse,
)
from app.workflows.graph import build_workflow_graph
from app.workflows.nodes import finalization_node, revision_handler_node
from app.workflows.state import MultiAgentWorkflowState

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Business service layer managing LangGraph multi-agent orchestration,
    human approval decision boundaries, revision loops, and workflow state persistence.
    """

    def __init__(self, db: AsyncSession, provider: Optional[LLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()
        self.graph = build_workflow_graph()

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

        # Administrators always have full permission
        if viewer_role in {"admin", "administrator"}:
            return cycle

        # Managers have permission to initiate, view, approve, and calibrate
        if viewer_role == "manager":
            return cycle

        if viewer_id is not None:
            # Cycle owner (manager / reviewer)
            if cycle.owner_id == viewer_id:
                return cycle

            # Subject employee: can view workflow status & draft, but CANNOT approve or request revision
            if cycle.employee_id == viewer_id:
                if action in {"approve", "request_revision", "cancel"}:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only managers, cycle owners, or administrators may approve, request revisions, or cancel workflows",
                    )
                return cycle

            # Unrelated user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have authorization to view or execute workflows on this review cycle",
            )

        return cycle

    def _determine_available_actions(self, workflow_status: str, viewer_role: Optional[str]) -> List[str]:
        is_manager_or_admin = viewer_role in {"manager", "admin", "administrator"}
        if workflow_status == "awaiting_approval":
            if is_manager_or_admin:
                return ["approve", "request_revision", "cancel"]
            return []
        elif workflow_status == "revision_requested":
            return ["resume", "cancel"] if is_manager_or_admin else []
        elif workflow_status in {"failed", "cancelled"}:
            return ["start"] if is_manager_or_admin else []
        elif workflow_status == "completed":
            return []
        return []

    def _build_status_response(
        self,
        run: WorkflowRun,
        state: Dict[str, Any],
        viewer_role: Optional[str],
    ) -> WorkflowStatusResponse:
        stages_data: List[WorkflowStageStatus] = [
            WorkflowStageStatus(
                stage_name="evidence_retrieval",
                display_title="1. Evidence Retrieval Agent",
                status="completed" if state.get("evidence_items") is not None else "pending",
                description="Scopes and extracts authorized commit, PR, and document artifacts.",
                summary_data={
                    "evidence_count": state.get("evidence_count", 0),
                    "completeness_score": state.get("evidence_completeness_score", 0.0),
                    "gaps_count": len(state.get("evidence_gaps", [])),
                },
            ),
            WorkflowStageStatus(
                stage_name="feedback_analysis",
                display_title="2. Feedback Analysis Agent",
                status="completed" if state.get("feedback_findings") is not None else "pending",
                description="Synthesizes self, peer, and manager observations into grounded findings.",
                summary_data={
                    "strengths_count": len(state.get("strengths", [])),
                    "growth_areas_count": len(state.get("improvement_opportunities", [])),
                    "contradictions_count": len(state.get("contradictions", [])),
                },
            ),
            WorkflowStageStatus(
                stage_name="bias_audit",
                display_title="3. Bias & Quality Auditor",
                status="completed" if state.get("audit_health_score") is not None else "pending",
                description="Evaluates 5 deterministic rules: recency bias, stakeholder coverage, ungrounded claims, vague language, contradictions.",
                summary_data={
                    "audit_health_score": state.get("audit_health_score", 100.0),
                    "is_ready_for_review": state.get("is_ready_for_review", False),
                    "total_flags": len(state.get("audit_flags", [])),
                },
            ),
            WorkflowStageStatus(
                stage_name="review_synthesis",
                display_title="4. Review Synthesis Agent",
                status="completed" if state.get("draft_report") is not None else "pending",
                description="Drafts a comprehensive, grounded review report without automated compensation or termination decisions.",
                summary_data={
                    "has_draft": state.get("draft_report") is not None,
                    "citations_count": len(state.get("draft_report", {}).get("citations", [])),
                },
            ),
            WorkflowStageStatus(
                stage_name="human_approval_pause",
                display_title="5. Human Approval Pause Node",
                status=(
                    "completed"
                    if run.workflow_status in {"approved", "completed"}
                    else (
                        "paused"
                        if run.workflow_status == "awaiting_approval"
                        else ("revision_requested" if run.workflow_status == "revision_requested" else "pending")
                    )
                ),
                description="Mandatory human decision boundary. Halts execution until an authorized reviewer approves or requests revisions.",
                summary_data={
                    "approval_decision": state.get("approval_decision"),
                    "reviewer_id": state.get("reviewer_id"),
                },
            ),
        ]

        # Extract draft report if present
        draft_dict = state.get("draft_report")
        draft_obj: Optional[WorkflowDraftReport] = None
        if draft_dict:
            draft_obj = WorkflowDraftReport(
                cycle_id=draft_dict.get("cycle_id", str(run.cycle_id)),
                employee_id=draft_dict.get("employee_id", ""),
                version_number=draft_dict.get("version_number", 1),
                status=draft_dict.get("status", "draft"),
                executive_summary=draft_dict.get("executive_summary", ""),
                strengths=draft_dict.get("strengths", []),
                growth_areas=draft_dict.get("growth_areas", []),
                goal_progress=draft_dict.get("goal_progress", []),
                impact_highlights=draft_dict.get("impact_highlights", []),
                bias_audit_summary=draft_dict.get("bias_audit_summary", {}),
                evidence_gaps_and_limitations=draft_dict.get("evidence_gaps_and_limitations", []),
                suggested_discussion_questions=draft_dict.get("suggested_discussion_questions", []),
                citations=draft_dict.get("citations", []),
            )

        available_actions = self._determine_available_actions(run.workflow_status, viewer_role)

        approval_metadata = None
        if state.get("approval_decision"):
            approval_metadata = {
                "decision": state.get("approval_decision"),
                "reviewer_id": state.get("reviewer_id"),
                "reviewer_role": state.get("reviewer_role"),
                "reviewer_comments": state.get("reviewer_comments"),
                "comments": state.get("reviewer_comments"),
                "approval_timestamp": state.get("approval_timestamp"),
            }

        return WorkflowStatusResponse(
            run_id=run.id,
            cycle_id=run.cycle_id,
            employee_id=uuid.UUID(state.get("employee_id")) if state.get("employee_id") else None,
            workflow_status=run.workflow_status,
            current_stage=run.current_stage,
            stages=stages_data,
            draft_report=draft_obj,
            audit_health_score=state.get("audit_health_score"),
            is_ready_for_review=state.get("is_ready_for_review"),
            audit_flags_count=len(state.get("audit_flags", [])),
            available_actions=available_actions,
            approval_metadata=approval_metadata,
            error_summary=run.error_metadata,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    # -----------------------------------------------------------------------
    # Public Workflow Lifecycle Methods
    # -----------------------------------------------------------------------

    async def start_workflow(
        self,
        cycle_id: uuid.UUID,
        request_in: Optional[WorkflowStartRequest] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Initiates a multi-agent review analysis workflow on an authorized review cycle.
        Executes agents 1-4 and pauses at the HumanApprovalPauseNode.
        """
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="start"
        )
        req = request_in or WorkflowStartRequest()

        # Idempotency check: Return existing active or awaiting_approval run if not forcing re-run
        if not req.force_re_run:
            active_run = await WorkflowRepository.get_active_run_for_cycle(self.db, cycle.id)
            if active_run:
                logger.info("Found existing active workflow run=%s for cycle=%s", active_run.id, cycle.id)
                return self._build_status_response(active_run, active_run.stage_state or {}, viewer_role)

        # 1. Initialize persistent WorkflowRun record
        run = await WorkflowRepository.create_workflow_run(
            db=self.db,
            cycle_id=cycle.id,
            workflow_status="running",
            current_stage="evidence_retrieval",
            stage_state={},
            provider_metadata={"provider": self.provider.name, "model": self.provider.model_name},
        )

        initial_state: MultiAgentWorkflowState = {
            "run_id": str(run.id),
            "cycle_id": str(cycle.id),
            "employee_id": str(cycle.employee_id),
            "initiating_user_id": str(viewer_id) if viewer_id else None,
            "initiating_user_role": viewer_role,
            "status": "running",
            "current_stage": "evidence_retrieval",
            "max_evidence_items": req.max_evidence_items or 50,
            "errors": [],
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }

        # 2. Execute graph through agents 1-4 up to HumanApprovalPauseNode
        config = {"configurable": {"db": self.db, "provider": self.provider}}
        try:
            final_state = await self.graph.ainvoke(initial_state, config=config)
            workflow_status = final_state.get("status", "awaiting_approval")
            current_stage = final_state.get("current_stage", "human_approval_pause")

            # Update database record
            run = await WorkflowRepository.update_workflow_run(
                db=self.db,
                run=run,
                workflow_status=workflow_status,
                current_stage=current_stage,
                stage_state=final_state,
            )

            # Log audit event
            await WorkflowRepository.record_audit_event(
                db=self.db,
                action="workflow.started",
                resource_type="workflow_run",
                resource_id=str(run.id),
                actor_id=viewer_id,
                metadata_json={"cycle_id": str(cycle.id), "status": workflow_status},
            )

            return self._build_status_response(run, final_state, viewer_role)

        except Exception as exc:
            logger.exception("Multi-agent workflow execution failed for run=%s: %s", run.id, exc)
            run = await WorkflowRepository.update_workflow_run(
                db=self.db,
                run=run,
                workflow_status="failed",
                current_stage="failed",
                error_metadata={"error": str(exc), "stage": initial_state.get("current_stage")},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow execution failed: {str(exc)}",
            )

    async def get_workflow(
        self,
        workflow_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """Retrieves current workflow execution state, draft report, and available actions."""
        run = await WorkflowRepository.get_by_id(self.db, workflow_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow run with ID '{workflow_id}' not found",
            )

        # Scoping & authorization check
        await self._verify_cycle_and_permissions(
            run.cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="view"
        )

        return self._build_status_response(run, run.stage_state or {}, viewer_role)

    async def approve_workflow(
        self,
        workflow_id: uuid.UUID,
        request_in: WorkflowApprovalRequest,
        reviewer_id: uuid.UUID,
        reviewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Records authorized human manager approval, resumes workflow, and finalizes the review report.
        """
        run = await WorkflowRepository.get_by_id(self.db, workflow_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow run with ID '{workflow_id}' not found",
            )

        # Enforce manager / administrator role
        await self._verify_cycle_and_permissions(
            run.cycle_id, viewer_id=reviewer_id, viewer_role=reviewer_role, action="approve"
        )

        if run.workflow_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workflow run has already been completed and approved",
            )

        if run.workflow_status not in {"awaiting_approval", "running"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve workflow in '{run.workflow_status}' state (must be 'awaiting_approval')",
            )

        # Update state with approval decision
        state = dict(run.stage_state or {})
        state["approval_decision"] = "approved"
        state["reviewer_id"] = str(reviewer_id)
        state["reviewer_role"] = reviewer_role
        state["reviewer_comments"] = request_in.comments

        # Execute finalization node
        config = {"configurable": {"db": self.db, "provider": self.provider}}
        final_state = await finalization_node(state, config=config)
        merged_state = {**state, **final_state}

        run = await WorkflowRepository.update_workflow_run(
            db=self.db,
            run=run,
            workflow_status="completed",
            current_stage="completed",
            stage_state=merged_state,
        )

        return self._build_status_response(run, merged_state, reviewer_role)

    async def request_revision(
        self,
        workflow_id: uuid.UUID,
        request_in: WorkflowRevisionRequest,
        reviewer_id: uuid.UUID,
        reviewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Records human manager revision instructions, marks draft as revision_requested,
        and halts finalization.
        """
        run = await WorkflowRepository.get_by_id(self.db, workflow_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow run with ID '{workflow_id}' not found",
            )

        await self._verify_cycle_and_permissions(
            run.cycle_id, viewer_id=reviewer_id, viewer_role=reviewer_role, action="request_revision"
        )

        if run.workflow_status not in {"awaiting_approval", "running"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot request revision on workflow in '{run.workflow_status}' state (must be 'awaiting_approval')",
            )

        state = dict(run.stage_state or {})
        state["approval_decision"] = "revision_requested"
        state["reviewer_id"] = str(reviewer_id)
        state["reviewer_role"] = reviewer_role
        state["reviewer_comments"] = request_in.revision_instructions

        config = {"configurable": {"db": self.db, "provider": self.provider}}
        rev_state = await revision_handler_node(state, config=config)
        merged_state = {**state, **rev_state}

        run = await WorkflowRepository.update_workflow_run(
            db=self.db,
            run=run,
            workflow_status="revision_requested",
            current_stage="revision_handling",
            stage_state=merged_state,
        )

        return self._build_status_response(run, merged_state, reviewer_role)

    async def resume_workflow(
        self,
        workflow_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Safely resumes an interrupted or paused workflow from persisted state.
        """
        run = await WorkflowRepository.get_by_id(self.db, workflow_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow run with ID '{workflow_id}' not found",
            )

        await self._verify_cycle_and_permissions(
            run.cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="start"
        )

        if run.workflow_status == "completed":
            return self._build_status_response(run, run.stage_state or {}, viewer_role)

        if run.workflow_status == "awaiting_approval":
            # Already paused at human approval boundary; return current state cleanly
            return self._build_status_response(run, run.stage_state or {}, viewer_role)

        # Otherwise resume graph from saved state
        state = dict(run.stage_state or {})
        config = {"configurable": {"db": self.db, "provider": self.provider}}
        final_state = await self.graph.ainvoke(state, config=config)

        run = await WorkflowRepository.update_workflow_run(
            db=self.db,
            run=run,
            workflow_status=final_state.get("status", "awaiting_approval"),
            current_stage=final_state.get("current_stage", "human_approval_pause"),
            stage_state=final_state,
        )

        return self._build_status_response(run, final_state, viewer_role)

    async def cancel_workflow(
        self,
        workflow_id: uuid.UUID,
        request_in: WorkflowCancelRequest,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> WorkflowStatusResponse:
        """
        Cancels an ongoing or paused workflow run.
        """
        run = await WorkflowRepository.get_by_id(self.db, workflow_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow run with ID '{workflow_id}' not found",
            )

        await self._verify_cycle_and_permissions(
            run.cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="cancel"
        )

        if run.workflow_status in {"completed", "cancelled"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel workflow in '{run.workflow_status}' terminal status",
            )

        state = dict(run.stage_state or {})
        state["status"] = "cancelled"
        state["approval_decision"] = "cancelled"
        state["reviewer_comments"] = request_in.reason

        run = await WorkflowRepository.update_workflow_run(
            db=self.db,
            run=run,
            workflow_status="cancelled",
            current_stage="cancelled",
            stage_state=state,
        )

        await WorkflowRepository.record_audit_event(
            db=self.db,
            action="workflow.cancelled",
            resource_type="workflow_run",
            resource_id=str(run.id),
            actor_id=viewer_id,
            metadata_json={"reason": request_in.reason},
        )

        return self._build_status_response(run, state, viewer_role)

    async def list_workflows_for_cycle(
        self,
        cycle_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        limit: int = 50,
    ) -> WorkflowListResponse:
        """Lists historical and active workflow runs for a review cycle."""
        cycle = await self._verify_cycle_and_permissions(
            cycle_id, viewer_id=viewer_id, viewer_role=viewer_role, action="view"
        )

        runs = await WorkflowRepository.list_for_cycle(self.db, cycle.id, limit=limit)
        items = [self._build_status_response(r, r.stage_state or {}, viewer_role) for r in runs]

        return WorkflowListResponse(
            cycle_id=cycle.id,
            total_count=len(items),
            workflows=items,
        )

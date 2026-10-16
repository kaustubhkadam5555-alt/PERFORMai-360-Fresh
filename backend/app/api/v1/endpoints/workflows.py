import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import resolve_principal, verify_manager_or_admin
from app.db.session import get_db
from app.schemas.workflow import (
    WorkflowApprovalRequest,
    WorkflowCancelRequest,
    WorkflowListResponse,
    WorkflowRevisionRequest,
    WorkflowStartRequest,
    WorkflowStatusResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(tags=["workflows"])


# ---------------------------------------------------------------------------
# Cycle-Scoped Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/review-cycles/{cycle_id}/workflows",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a multi-agent review analysis workflow",
    description="Initiates the 4 specialist agents (Evidence, Feedback, Bias, Synthesis) up to the Human Approval Pause Node.",
)
@router.post(
    "/review-cycles/{cycle_id}/workflow-runs",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a multi-agent review analysis workflow (alias endpoint)",
    include_in_schema=True,
)
async def start_workflow(
    cycle_id: uuid.UUID,
    request_in: Optional[WorkflowStartRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="manager",
    )
    service = WorkflowService(db)
    return await service.start_workflow(
        cycle_id=cycle_id,
        request_in=request_in,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/review-cycles/{cycle_id}/workflows",
    response_model=WorkflowListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflow runs for a review cycle",
    description="Returns all active and historical workflow runs for the specified cycle.",
)
async def list_cycle_workflows(
    cycle_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="employee",
    )
    service = WorkflowService(db)
    return await service.list_workflows_for_cycle(
        cycle_id=cycle_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Workflow-Scoped Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve workflow execution status and draft report",
    description="Returns current stage, agent summaries, draft report, audit flags, and available reviewer actions.",
)
async def get_workflow(
    workflow_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="employee",
    )
    service = WorkflowService(db)
    return await service.get_workflow(
        workflow_id=workflow_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.post(
    "/workflows/{workflow_id}/approve",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve workflow draft report (Human-in-the-Loop decision)",
    description="Records human approval sign-off, finalizes the review report, and logs an immutable audit event.",
)
async def approve_workflow(
    workflow_id: uuid.UUID,
    request_in: Optional[WorkflowApprovalRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Reviewer user ID"),
    viewer_role: Optional[str] = Query(default=None, description="Reviewer role (must be manager or admin)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="employee",
    )
    if not effective_viewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer identity is required for workflow approval.",
        )
    verify_manager_or_admin(effective_viewer_role)

    payload = request_in or WorkflowApprovalRequest()
    service = WorkflowService(db)
    return await service.approve_workflow(
        workflow_id=workflow_id,
        request_in=payload,
        reviewer_id=effective_viewer_id,
        reviewer_role=effective_viewer_role,
    )


@router.post(
    "/workflows/{workflow_id}/request-revision",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Request revisions on workflow draft report",
    description="Records reviewer change instructions, marks draft as revision_requested, and halts finalization.",
)
async def request_revision(
    workflow_id: uuid.UUID,
    request_in: WorkflowRevisionRequest,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Reviewer user ID"),
    viewer_role: Optional[str] = Query(default=None, description="Reviewer role (manager or admin)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="employee",
    )
    if not effective_viewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer identity is required to request workflow revisions.",
        )
    verify_manager_or_admin(effective_viewer_role)

    service = WorkflowService(db)
    return await service.request_revision(
        workflow_id=workflow_id,
        request_in=request_in,
        reviewer_id=effective_viewer_id,
        reviewer_role=effective_viewer_role,
    )


@router.post(
    "/workflows/{workflow_id}/resume",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Safely resume an interrupted or paused workflow",
    description="Resumes execution from persisted state checkpoint.",
)
async def resume_workflow(
    workflow_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="manager",
    )
    verify_manager_or_admin(effective_viewer_role)
    service = WorkflowService(db)
    return await service.resume_workflow(
        workflow_id=workflow_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.post(
    "/workflows/{workflow_id}/cancel",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a workflow run",
    description="Transitions an ongoing or paused workflow to cancelled status.",
)
async def cancel_workflow(
    workflow_id: uuid.UUID,
    request_in: Optional[WorkflowCancelRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    effective_viewer_id, effective_viewer_role = resolve_principal(
        header_id=x_viewer_id,
        header_role=x_viewer_role,
        query_id=viewer_id,
        query_role=viewer_role,
        default_role="manager",
    )
    verify_manager_or_admin(effective_viewer_role)
    payload = request_in or WorkflowCancelRequest()
    service = WorkflowService(db)
    return await service.cancel_workflow(
        workflow_id=workflow_id,
        request_in=payload,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )

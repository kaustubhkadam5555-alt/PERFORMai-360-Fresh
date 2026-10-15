import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.bias_flag import (
    AuditExecutionRequest,
    AuditSummaryResponse,
    BiasFlagResponse,
    BiasFlagUpdate,
)
from app.services.bias_audit_service import BiasAuditService

router = APIRouter(prefix="/review-cycles", tags=["Bias & Evidence Audit"])


@router.post(
    "/{cycle_id}/audit",
    response_model=AuditSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute deterministic bias and evidence-quality audit on a review cycle",
)
@router.post(
    "/{cycle_id}/bias-audit",
    response_model=AuditSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute deterministic bias and evidence-quality audit (alias endpoint)",
    include_in_schema=True,
)
async def run_bias_audit(
    cycle_id: uuid.UUID,
    request_in: Optional[AuditExecutionRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> AuditSummaryResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = BiasAuditService(db)
    return await service.execute_audit(
        cycle_id=cycle_id,
        request_in=request_in,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/{cycle_id}/audit-flags",
    response_model=List[BiasFlagResponse],
    summary="List bias and evidence-quality flags for a review cycle",
)
@router.get(
    "/{cycle_id}/bias-flags",
    response_model=List[BiasFlagResponse],
    summary="List bias and evidence-quality flags (alias endpoint)",
    include_in_schema=True,
)
async def list_audit_flags(
    cycle_id: uuid.UUID,
    status: Optional[str] = Query(default=None, description="Filter: open, acknowledged, resolved, not_applicable"),
    flag_type: Optional[str] = Query(
        default=None, description="Filter: evidence_coverage, recency_concentration, etc."
    ),
    severity: Optional[str] = Query(default=None, description="Filter: low, medium, high, review"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> List[BiasFlagResponse]:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = BiasAuditService(db)
    return await service.list_flags(
        cycle_id=cycle_id,
        status_filter=status,
        flag_type_filter=flag_type,
        severity_filter=severity,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/{cycle_id}/audit-summary",
    response_model=AuditSummaryResponse,
    summary="Get aggregated audit health score, status distribution, and flag listing",
)
async def get_audit_summary(
    cycle_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> AuditSummaryResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = BiasAuditService(db)
    return await service.get_audit_summary(
        cycle_id=cycle_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.patch(
    "/{cycle_id}/audit-flags/{flag_id}",
    response_model=BiasFlagResponse,
    summary="Update audit flag status and record reviewer calibration comments",
)
@router.patch(
    "/{cycle_id}/bias-flags/{flag_id}",
    response_model=BiasFlagResponse,
    summary="Update audit flag status (alias endpoint)",
    include_in_schema=True,
)
async def update_audit_flag(
    cycle_id: uuid.UUID,
    flag_id: uuid.UUID,
    flag_update: BiasFlagUpdate,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> BiasFlagResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = BiasAuditService(db)
    return await service.update_flag(
        cycle_id=cycle_id,
        flag_id=flag_id,
        flag_update=flag_update,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )

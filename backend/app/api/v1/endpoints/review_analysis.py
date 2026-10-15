import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.review_analysis import (
    FindingResponse,
    ReviewAnalysisRequest,
    ReviewAnalysisResponse,
)
from app.services.review_analysis_service import ReviewAnalysisService

router = APIRouter(prefix="/review-cycles", tags=["Review Analysis"])


@router.post(
    "/{cycle_id}/analysis",
    response_model=ReviewAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute evidence-grounded review analysis for a cycle",
)
@router.post(
    "/{cycle_id}/analysis-runs",
    response_model=ReviewAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute evidence-grounded review analysis (alias endpoint)",
    include_in_schema=True,
)
async def run_review_analysis(
    cycle_id: uuid.UUID,
    request_in: Optional[ReviewAnalysisRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalysisResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReviewAnalysisService(db)
    return await service.execute_analysis(
        cycle_id=cycle_id,
        request_in=request_in,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/{cycle_id}/analysis",
    response_model=ReviewAnalysisResponse,
    summary="Get latest review analysis for a cycle",
)
async def get_latest_review_analysis(
    cycle_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalysisResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReviewAnalysisService(db)
    result = await service.get_latest_analysis_for_cycle(
        cycle_id=cycle_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for review cycle '{cycle_id}'",
        )
    return result


@router.get(
    "/{cycle_id}/analysis/{analysis_id}",
    response_model=ReviewAnalysisResponse,
    summary="Get review analysis by ID",
)
async def get_review_analysis_by_id(
    cycle_id: uuid.UUID,
    analysis_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalysisResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReviewAnalysisService(db)
    return await service.get_analysis_by_id(
        cycle_id=cycle_id,
        analysis_id=analysis_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/{cycle_id}/findings",
    response_model=List[FindingResponse],
    summary="List atomic findings extracted from review analysis",
)
async def list_cycle_findings(
    cycle_id: uuid.UUID,
    finding_type: Optional[str] = Query(
        default=None, description="Filter: strength, improvement_opportunity, contradiction"
    ),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> List[FindingResponse]:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReviewAnalysisService(db)
    return await service.list_findings_for_cycle(
        cycle_id=cycle_id,
        finding_type=finding_type,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )

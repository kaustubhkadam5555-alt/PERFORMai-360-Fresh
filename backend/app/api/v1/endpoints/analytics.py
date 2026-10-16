import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    AuditAnalyticsResponse,
    EvidenceAnalyticsResponse,
    ReviewAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get high-level evaluation analytics overview",
    description="Aggregates review cycle totals, completion rates, report statuses, evidence volume, approval ratios, and audit scores.",
)
async def get_analytics_overview(
    team_id: Optional[uuid.UUID] = Query(default=None, description="Optional team filter"),
    start_date: Optional[date] = Query(default=None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="End date filter (YYYY-MM-DD)"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = AnalyticsService(db)
    return await service.get_overview(
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/reviews",
    response_model=ReviewAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get review cycle lifecycle and duration metrics",
    description="Returns cycle completion rates, status distributions, average evaluation durations, and per-cycle status summaries.",
)
async def get_review_analytics(
    team_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReviewAnalyticsResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = AnalyticsService(db)
    return await service.get_reviews(
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/evidence",
    response_model=EvidenceAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get evidence coverage and citation grounding analytics",
    description="Analyzes evidence distribution by source type, access policy classifications, cited findings vs ungrounded claims, and coverage percentage.",
)
async def get_evidence_analytics(
    team_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> EvidenceAnalyticsResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = AnalyticsService(db)
    return await service.get_evidence(
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/audits",
    response_model=AuditAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bias and evidence-quality audit statistics",
    description="Aggregates deterministic bias audit findings by rule category, severity levels, resolution statuses, and health score distribution.",
)
async def get_audit_analytics(
    team_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> AuditAnalyticsResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = AnalyticsService(db)
    return await service.get_audits(
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/trends",
    response_model=AnalyticsTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chronological evaluation trends",
    description="Provides chronological activity trends (cycles created, reports approved, evidence uploaded, feedback submitted, bias flags raised) over time.",
)
async def get_analytics_trends(
    interval: str = Query(default="month", description="Aggregation interval ('month')"),
    limit: int = Query(default=12, ge=1, le=36, description="Number of chronological buckets"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsTrendsResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = AnalyticsService(db)
    return await service.get_trends(
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        interval=interval,
        limit=limit,
    )

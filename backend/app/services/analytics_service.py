import logging
import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    AuditAnalyticsResponse,
    CycleAnalyticsItem,
    EvidenceAnalyticsResponse,
    ReviewAnalyticsResponse,
    TrendPoint,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service layer for Phase 9 Analytics.
    Validates filter constraints, enforces RBAC scoping, and serializes aggregate metrics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_date_range(self, start_date: Optional[date], end_date: Optional[date]) -> None:
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid date range: start_date ({start_date}) cannot be after end_date ({end_date}).",
            )

    async def get_overview(
        self,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AnalyticsOverviewResponse:
        self._validate_date_range(start_date, end_date)
        raw = await AnalyticsRepository.get_overview(
            db=self.db,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        return AnalyticsOverviewResponse(**raw)

    async def get_reviews(
        self,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ReviewAnalyticsResponse:
        self._validate_date_range(start_date, end_date)
        raw = await AnalyticsRepository.get_reviews(
            db=self.db,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        raw["cycles"] = [CycleAnalyticsItem(**item) for item in raw.get("cycles", [])]
        return ReviewAnalyticsResponse(**raw)

    async def get_evidence(
        self,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> EvidenceAnalyticsResponse:
        self._validate_date_range(start_date, end_date)
        raw = await AnalyticsRepository.get_evidence_analytics(
            db=self.db,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        return EvidenceAnalyticsResponse(**raw)

    async def get_audits(
        self,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AuditAnalyticsResponse:
        self._validate_date_range(start_date, end_date)
        raw = await AnalyticsRepository.get_audit_analytics(
            db=self.db,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        return AuditAnalyticsResponse(**raw)

    async def get_trends(
        self,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        interval: str = "month",
        limit: int = 12,
    ) -> AnalyticsTrendsResponse:
        raw_points = await AnalyticsRepository.get_trends(
            db=self.db,
            viewer_id=viewer_id,
            viewer_role=viewer_role,
            interval=interval,
            limit=limit,
        )
        points = [TrendPoint(**p) for p in raw_points]
        return AnalyticsTrendsResponse(
            interval=interval,
            total_points=len(points),
            trends=points,
        )

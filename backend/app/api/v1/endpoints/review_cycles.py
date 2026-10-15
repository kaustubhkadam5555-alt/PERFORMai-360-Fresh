import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.review_cycle import (
    ReviewCycleCreate,
    ReviewCycleResponse,
    ReviewCycleUpdate,
)
from app.services.review_cycle_service import ReviewCycleService

router = APIRouter(prefix="/review-cycles", tags=["Review Cycles"])


@router.get("", response_model=List[ReviewCycleResponse], summary="List review cycles")
async def list_review_cycles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    employee_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> List[ReviewCycleResponse]:
    service = ReviewCycleService(db)
    return await service.list_cycles(skip=skip, limit=limit, employee_id=employee_id, status_filter=status_filter)


@router.post(
    "",
    response_model=ReviewCycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review cycle",
)
async def create_review_cycle(
    cycle_in: ReviewCycleCreate,
    db: AsyncSession = Depends(get_db),
) -> ReviewCycleResponse:
    service = ReviewCycleService(db)
    return await service.create_cycle(cycle_in)


@router.get("/{cycle_id}", response_model=ReviewCycleResponse, summary="Get review cycle by ID")
async def get_review_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReviewCycleResponse:
    service = ReviewCycleService(db)
    return await service.get_cycle_by_id(cycle_id)


@router.patch("/{cycle_id}", response_model=ReviewCycleResponse, summary="Update review cycle")
async def update_review_cycle(
    cycle_id: uuid.UUID,
    cycle_in: ReviewCycleUpdate,
    db: AsyncSession = Depends(get_db),
) -> ReviewCycleResponse:
    service = ReviewCycleService(db)
    return await service.update_cycle(cycle_id, cycle_in)

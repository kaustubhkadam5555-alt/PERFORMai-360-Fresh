import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.goal import GoalCreate, GoalResponse
from app.schemas.review_cycle import (
    ReviewCycleCreate,
    ReviewCycleResponse,
    ReviewCycleUpdate,
)
from app.services.evidence_service import EvidenceService
from app.services.feedback_service import FeedbackService
from app.services.goal_service import GoalService
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


@router.delete("/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete draft review cycle")
async def delete_review_cycle(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ReviewCycleService(db)
    await service.delete_cycle(cycle_id)


# --- Nested Review Cycle Endpoints (PRD Section 11) ---


@router.get(
    "/{cycle_id}/feedback",
    response_model=List[FeedbackResponse],
    summary="List feedback for a review cycle",
)
async def list_cycle_feedback(
    cycle_id: uuid.UUID,
    feedback_type: Optional[str] = Query(default=None),
    author_id: Optional[uuid.UUID] = Query(default=None),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[FeedbackResponse]:
    service = FeedbackService(db)
    return await service.list_feedback(
        cycle_id=cycle_id,
        feedback_type=feedback_type,
        author_id=author_id,
        viewer_id=viewer_id or x_viewer_id,
        viewer_role=viewer_role or x_viewer_role,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{cycle_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback for a review cycle",
)
async def submit_cycle_feedback(
    cycle_id: uuid.UUID,
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    service = FeedbackService(db)
    return await service.create_feedback(cycle_id=cycle_id, feedback_in=feedback_in)


@router.get(
    "/{cycle_id}/goals",
    response_model=List[GoalResponse],
    summary="List goals for a review cycle",
)
async def list_cycle_goals(
    cycle_id: uuid.UUID,
    goal_status: Optional[str] = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[GoalResponse]:
    service = GoalService(db)
    return await service.list_goals(cycle_id=cycle_id, goal_status=goal_status, skip=skip, limit=limit)


@router.post(
    "/{cycle_id}/goals",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a goal for a review cycle",
)
async def create_cycle_goal(
    cycle_id: uuid.UUID,
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    service = GoalService(db)
    return await service.create_goal(cycle_id=cycle_id, goal_in=goal_in)


@router.get(
    "/{cycle_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="List evidence for a review cycle",
)
async def list_cycle_evidence(
    cycle_id: uuid.UUID,
    source_type: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[EvidenceResponse]:
    service = EvidenceService(db)
    return await service.list_evidence(
        cycle_id=cycle_id,
        source_type=source_type,
        start_date=start_date,
        end_date=end_date,
        viewer_id=viewer_id or x_viewer_id,
        viewer_role=viewer_role or x_viewer_role,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{cycle_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register evidence for a review cycle",
)
async def register_cycle_evidence(
    cycle_id: uuid.UUID,
    evidence_in: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    service = EvidenceService(db)
    return await service.create_evidence(cycle_id=cycle_id, evidence_in=evidence_in)

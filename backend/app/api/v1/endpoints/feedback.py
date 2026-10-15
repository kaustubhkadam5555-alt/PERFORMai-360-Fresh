import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackUpdate
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("", response_model=List[FeedbackResponse], summary="List feedback records")
async def list_feedback(
    cycle_id: Optional[uuid.UUID] = Query(default=None, description="Filter by review cycle ID"),
    employee_id: Optional[uuid.UUID] = Query(default=None, description="Filter by subject employee ID"),
    author_id: Optional[uuid.UUID] = Query(default=None, description="Filter by author user ID"),
    feedback_type: Optional[str] = Query(default=None, description="Filter by feedback type: self, peer, manager"),
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for visibility checks"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (employee, manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[FeedbackResponse]:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = FeedbackService(db)
    return await service.list_feedback(
        cycle_id=cycle_id,
        subject_employee_id=employee_id,
        author_id=author_id,
        feedback_type=feedback_type,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    if not feedback_in.cycle_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="cycle_id must be provided in request body when creating feedback via /feedback",
        )
    service = FeedbackService(db)
    return await service.create_feedback(cycle_id=feedback_in.cycle_id, feedback_in=feedback_in)


@router.get("/{feedback_id}", response_model=FeedbackResponse, summary="Get feedback by ID")
async def get_feedback(
    feedback_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = FeedbackService(db)
    return await service.get_feedback_by_id(
        feedback_id, viewer_id=effective_viewer_id, viewer_role=effective_viewer_role
    )


@router.patch("/{feedback_id}", response_model=FeedbackResponse, summary="Update feedback")
async def update_feedback(
    feedback_id: uuid.UUID,
    feedback_in: FeedbackUpdate,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    service = FeedbackService(db)
    return await service.update_feedback(feedback_id, feedback_in, viewer_id=viewer_id or x_viewer_id)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete feedback")
async def delete_feedback(
    feedback_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = FeedbackService(db)
    await service.delete_feedback(feedback_id, viewer_id=viewer_id or x_viewer_id)

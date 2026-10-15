import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from app.services.goal_service import GoalService

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("", response_model=List[GoalResponse], summary="List goals")
async def list_goals(
    cycle_id: Optional[uuid.UUID] = Query(default=None, description="Filter by review cycle ID"),
    employee_id: Optional[uuid.UUID] = Query(default=None, description="Filter by employee ID"),
    goal_status: Optional[str] = Query(default=None, alias="status", description="Filter by goal status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[GoalResponse]:
    service = GoalService(db)
    return await service.list_goals(
        cycle_id=cycle_id,
        employee_id=employee_id,
        goal_status=goal_status,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a goal",
)
async def create_goal(
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    if not goal_in.cycle_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="cycle_id must be provided in request body when creating goal via /goals",
        )
    service = GoalService(db)
    return await service.create_goal(cycle_id=goal_in.cycle_id, goal_in=goal_in)


@router.get("/{goal_id}", response_model=GoalResponse, summary="Get goal by ID")
async def get_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    service = GoalService(db)
    return await service.get_goal_by_id(goal_id)


@router.patch("/{goal_id}", response_model=GoalResponse, summary="Update goal")
async def update_goal(
    goal_id: uuid.UUID,
    goal_in: GoalUpdate,
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    service = GoalService(db)
    return await service.update_goal(goal_id, goal_in)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete goal")
async def delete_goal(
    goal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = GoalService(db)
    await service.delete_goal(goal_id)

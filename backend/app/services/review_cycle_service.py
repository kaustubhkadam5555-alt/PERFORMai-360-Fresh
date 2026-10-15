import uuid
from typing import Dict, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.review_cycle import ReviewCycleCreate, ReviewCycleUpdate

VALID_CYCLE_TRANSITIONS: Dict[str, Set[str]] = {
    ReviewCycleStatus.DRAFT.value: {
        ReviewCycleStatus.ACTIVE.value,
        ReviewCycleStatus.OPEN.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.ACTIVE.value: {
        ReviewCycleStatus.IN_REVIEW.value,
        ReviewCycleStatus.COLLECTING_FEEDBACK.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.OPEN.value: {
        ReviewCycleStatus.IN_REVIEW.value,
        ReviewCycleStatus.COLLECTING_FEEDBACK.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.COLLECTING_FEEDBACK.value: {
        ReviewCycleStatus.IN_REVIEW.value,
        ReviewCycleStatus.ANALYSIS_PENDING.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.IN_REVIEW.value: {
        ReviewCycleStatus.COMPLETED.value,
        ReviewCycleStatus.FINALIZED.value,
        ReviewCycleStatus.APPROVED.value,
        ReviewCycleStatus.ACTIVE.value,
        ReviewCycleStatus.OPEN.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.ANALYSIS_PENDING.value: {
        ReviewCycleStatus.DRAFT_REPORT.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.DRAFT_REPORT.value: {
        ReviewCycleStatus.CHANGES_REQUESTED.value,
        ReviewCycleStatus.APPROVED.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.CHANGES_REQUESTED.value: {
        ReviewCycleStatus.DRAFT_REPORT.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.APPROVED.value: {
        ReviewCycleStatus.COMPLETED.value,
        ReviewCycleStatus.FINALIZED.value,
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.COMPLETED.value: {
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.FINALIZED.value: {
        ReviewCycleStatus.ARCHIVED.value,
    },
    ReviewCycleStatus.ARCHIVED.value: set(),
}


class ReviewCycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cycle_by_id(self, cycle_id: uuid.UUID) -> ReviewCycle:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )
        return cycle

    async def list_cycles(
        self,
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[ReviewCycle]:
        return await ReviewCycleRepository.list_cycles(
            self.db, skip=skip, limit=limit, employee_id=employee_id, status=status_filter
        )

    async def create_cycle(self, cycle_in: ReviewCycleCreate) -> ReviewCycle:
        employee = await UserRepository.get_by_id(self.db, cycle_in.employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID '{cycle_in.employee_id}' does not exist",
            )
        owner = await UserRepository.get_by_id(self.db, cycle_in.owner_id)
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Review owner with ID '{cycle_in.owner_id}' does not exist",
            )
        if cycle_in.team_id:
            team = await TeamRepository.get_by_id(self.db, cycle_in.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team with ID '{cycle_in.team_id}' does not exist",
                )
        return await ReviewCycleRepository.create(self.db, cycle_in)

    async def update_cycle(self, cycle_id: uuid.UUID, cycle_in: ReviewCycleUpdate) -> ReviewCycle:
        cycle = await self.get_cycle_by_id(cycle_id)

        # Validate period date range against existing cycle dates if partial update
        effective_start = cycle_in.period_start if cycle_in.period_start is not None else cycle.period_start
        effective_end = cycle_in.period_end if cycle_in.period_end is not None else cycle.period_end
        if effective_end < effective_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="period_end must be on or after period_start",
            )

        # Validate lifecycle status transition if status is being updated
        if cycle_in.status is not None and cycle_in.status != cycle.status:
            current_status = cycle.status.lower()
            new_status = cycle_in.status.lower()
            allowed = VALID_CYCLE_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Invalid review cycle status transition from '{current_status}' to '{new_status}'. Allowed transitions: {sorted(allowed) if allowed else 'none (terminal state)'}",
                )

        if cycle_in.team_id:
            team = await TeamRepository.get_by_id(self.db, cycle_in.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team with ID '{cycle_in.team_id}' does not exist",
                )

        return await ReviewCycleRepository.update(self.db, cycle, cycle_in)

    async def delete_cycle(self, cycle_id: uuid.UUID) -> None:
        cycle = await self.get_cycle_by_id(cycle_id)
        if cycle.status != ReviewCycleStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete review cycle in '{cycle.status}' status. Only 'draft' cycles can be deleted.",
            )
        await ReviewCycleRepository.delete(self.db, cycle)

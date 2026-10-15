import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_cycle import ReviewCycle
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.review_cycle import ReviewCycleCreate, ReviewCycleUpdate


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
        if cycle_in.team_id:
            team = await TeamRepository.get_by_id(self.db, cycle_in.team_id)
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team with ID '{cycle_in.team_id}' does not exist",
                )
        return await ReviewCycleRepository.update(self.db, cycle, cycle_in)

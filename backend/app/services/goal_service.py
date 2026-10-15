import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.repositories.goal_repository import GoalRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.goal import GoalCreate, GoalUpdate


class GoalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_goal_by_id(self, goal_id: uuid.UUID) -> Goal:
        goal = await GoalRepository.get_by_id(self.db, goal_id)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found",
            )
        return goal

    async def list_goals(
        self,
        cycle_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        goal_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Goal]:
        if cycle_id:
            cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
            if not cycle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Review cycle with ID '{cycle_id}' not found",
                )
        if employee_id:
            emp = await UserRepository.get_by_id(self.db, employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{employee_id}' not found",
                )

        return await GoalRepository.list_goals(
            self.db,
            cycle_id=cycle_id,
            employee_id=employee_id,
            status=goal_status,
            skip=skip,
            limit=limit,
        )

    async def create_goal(self, cycle_id: uuid.UUID, goal_in: GoalCreate) -> Goal:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        if goal_in.employee_id is not None:
            emp = await UserRepository.get_by_id(self.db, goal_in.employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{goal_in.employee_id}' not found",
                )
            if goal_in.employee_id != cycle.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Employee ID '{goal_in.employee_id}' does not match review cycle employee ID '{cycle.employee_id}'",
                )

        return await GoalRepository.create(self.db, cycle_id, goal_in)

    async def update_goal(self, goal_id: uuid.UUID, goal_in: GoalUpdate) -> Goal:
        goal = await self.get_goal_by_id(goal_id)
        return await GoalRepository.update(self.db, goal, goal_in)

    async def delete_goal(self, goal_id: uuid.UUID) -> None:
        goal = await self.get_goal_by_id(goal_id)
        await GoalRepository.delete(self.db, goal)

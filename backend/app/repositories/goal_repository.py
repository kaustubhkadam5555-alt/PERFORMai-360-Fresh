import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal
from app.models.review_cycle import ReviewCycle
from app.schemas.goal import GoalCreate, GoalUpdate


class GoalRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, goal_id: uuid.UUID) -> Optional[Goal]:
        result = await db.execute(select(Goal).where(Goal.id == goal_id))
        return result.scalars().first()

    @staticmethod
    async def list_goals(
        db: AsyncSession,
        cycle_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Goal]:
        query = select(Goal).offset(skip).limit(limit).order_by(Goal.created_at.desc())
        if employee_id:
            query = query.join(ReviewCycle, Goal.cycle_id == ReviewCycle.id).where(
                ReviewCycle.employee_id == employee_id
            )
        if cycle_id:
            query = query.where(Goal.cycle_id == cycle_id)
        if status:
            query = query.where(Goal.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, cycle_id: uuid.UUID, goal_in: GoalCreate) -> Goal:
        goal = Goal(
            cycle_id=cycle_id,
            description=goal_in.description,
            measurable_target=goal_in.measurable_target,
            status=goal_in.status,
            due_date=goal_in.due_date,
            outcome_notes=goal_in.outcome_notes,
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return goal

    @staticmethod
    async def update(db: AsyncSession, db_goal: Goal, goal_in: GoalUpdate) -> Goal:
        update_data = goal_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_goal, field, value)
        await db.commit()
        await db.refresh(db_goal)
        return db_goal

    @staticmethod
    async def delete(db: AsyncSession, db_goal: Goal) -> None:
        await db.delete(db_goal)
        await db.commit()

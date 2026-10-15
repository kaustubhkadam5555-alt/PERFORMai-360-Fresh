import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_cycle import ReviewCycle
from app.schemas.review_cycle import ReviewCycleCreate, ReviewCycleUpdate


class ReviewCycleRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, cycle_id: uuid.UUID) -> Optional[ReviewCycle]:
        result = await db.execute(select(ReviewCycle).where(ReviewCycle.id == cycle_id))
        return result.scalars().first()

    @staticmethod
    async def list_cycles(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        employee_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[ReviewCycle]:
        query = select(ReviewCycle).offset(skip).limit(limit).order_by(ReviewCycle.created_at.desc())
        if employee_id:
            query = query.where(ReviewCycle.employee_id == employee_id)
        if status:
            query = query.where(ReviewCycle.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, cycle_in: ReviewCycleCreate) -> ReviewCycle:
        cycle = ReviewCycle(
            title=cycle_in.title,
            employee_id=cycle_in.employee_id,
            owner_id=cycle_in.owner_id,
            team_id=cycle_in.team_id,
            period_start=cycle_in.period_start,
            period_end=cycle_in.period_end,
            template_id=cycle_in.template_id,
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)
        return cycle

    @staticmethod
    async def update(db: AsyncSession, db_cycle: ReviewCycle, cycle_in: ReviewCycleUpdate) -> ReviewCycle:
        update_data = cycle_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_cycle, field, value)
        await db.commit()
        await db.refresh(db_cycle)
        return db_cycle

    @staticmethod
    async def delete(db: AsyncSession, db_cycle: ReviewCycle) -> None:
        await db.delete(db_cycle)
        await db.commit()

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate


class FeedbackRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, feedback_id: uuid.UUID) -> Optional[Feedback]:
        result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
        return result.scalars().first()

    @staticmethod
    async def list_feedback(
        db: AsyncSession,
        cycle_id: Optional[uuid.UUID] = None,
        subject_employee_id: Optional[uuid.UUID] = None,
        author_id: Optional[uuid.UUID] = None,
        feedback_type: Optional[str] = None,
        allowed_visibilities: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Feedback]:
        query = select(Feedback).offset(skip).limit(limit).order_by(Feedback.created_at.desc())
        if cycle_id:
            query = query.where(Feedback.cycle_id == cycle_id)
        if subject_employee_id:
            query = query.where(Feedback.subject_employee_id == subject_employee_id)
        if author_id:
            query = query.where(Feedback.author_id == author_id)
        if feedback_type:
            query = query.where(Feedback.feedback_type == feedback_type)
        if allowed_visibilities is not None:
            query = query.where(Feedback.visibility.in_(allowed_visibilities))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, cycle_id: uuid.UUID, feedback_in: FeedbackCreate) -> Feedback:
        feedback = Feedback(
            cycle_id=cycle_id,
            author_id=feedback_in.author_id,
            subject_employee_id=feedback_in.subject_employee_id,
            feedback_type=feedback_in.feedback_type,
            category=feedback_in.category,
            content=feedback_in.content,
            visibility=feedback_in.visibility,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    @staticmethod
    async def update(db: AsyncSession, db_feedback: Feedback, feedback_in: FeedbackUpdate) -> Feedback:
        update_data = feedback_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_feedback, field, value)
        await db.commit()
        await db.refresh(db_feedback)
        return db_feedback

    @staticmethod
    async def delete(db: AsyncSession, db_feedback: Feedback) -> None:
        await db.delete(db_feedback)
        await db.commit()

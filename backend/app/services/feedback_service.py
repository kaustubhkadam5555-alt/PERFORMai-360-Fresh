import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback, FeedbackType, FeedbackVisibility
from app.models.review_cycle import ReviewCycleStatus
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate

ACTIVE_SUBMISSION_STATUSES = {
    ReviewCycleStatus.ACTIVE.value,
    ReviewCycleStatus.OPEN.value,
    ReviewCycleStatus.COLLECTING_FEEDBACK.value,
}


class FeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feedback_by_id(
        self,
        feedback_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> Feedback:
        feedback = await FeedbackRepository.get_by_id(self.db, feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID '{feedback_id}' not found",
            )

        cycle = await ReviewCycleRepository.get_by_id(self.db, feedback.cycle_id)

        # Enforce visibility rules
        if not self._is_feedback_visible_to_viewer(feedback, cycle, viewer_id, viewer_role):
            # PRD Section 11: Return 404 when resource disclosure policy requires hiding existence
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID '{feedback_id}' not found",
            )

        return feedback

    async def list_feedback(
        self,
        cycle_id: Optional[uuid.UUID] = None,
        subject_employee_id: Optional[uuid.UUID] = None,
        author_id: Optional[uuid.UUID] = None,
        feedback_type: Optional[str] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Feedback]:
        # Validate cycle if provided
        cycle = None
        if cycle_id:
            cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
            if not cycle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Review cycle with ID '{cycle_id}' not found",
                )

        items = await FeedbackRepository.list_feedback(
            self.db,
            cycle_id=cycle_id,
            subject_employee_id=subject_employee_id,
            author_id=author_id,
            feedback_type=feedback_type,
            skip=skip,
            limit=limit,
        )

        # Filter items according to visibility
        visible_items = [
            item for item in items if self._is_feedback_visible_to_viewer(item, cycle, viewer_id, viewer_role)
        ]
        return visible_items

    async def create_feedback(self, cycle_id: uuid.UUID, feedback_in: FeedbackCreate) -> Feedback:
        # Validate cycle exists
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        # Validate cycle is in an active submission state
        if cycle.status.lower() not in ACTIVE_SUBMISSION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Feedback submissions are only permitted for active review cycles (current status: '{cycle.status}')",
            )

        # Validate author exists
        author = await UserRepository.get_by_id(self.db, feedback_in.author_id)
        if not author:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Author user with ID '{feedback_in.author_id}' not found",
            )

        # Validate subject exists
        subject = await UserRepository.get_by_id(self.db, feedback_in.subject_employee_id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject employee with ID '{feedback_in.subject_employee_id}' not found",
            )

        # Validate subject matches cycle employee
        if feedback_in.subject_employee_id != cycle.employee_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Subject employee ID '{feedback_in.subject_employee_id}' does not match review cycle employee ID '{cycle.employee_id}'",
            )

        # Validate relationship by feedback type
        if feedback_in.feedback_type == FeedbackType.SELF.value:
            if feedback_in.author_id != feedback_in.subject_employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Self feedback must have author_id matching subject_employee_id",
                )
        else:
            if feedback_in.author_id == feedback_in.subject_employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"{feedback_in.feedback_type.capitalize()} feedback author cannot be the subject employee",
                )

        return await FeedbackRepository.create(self.db, cycle_id, feedback_in)

    async def update_feedback(
        self,
        feedback_id: uuid.UUID,
        feedback_in: FeedbackUpdate,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> Feedback:
        feedback = await FeedbackRepository.get_by_id(self.db, feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID '{feedback_id}' not found",
            )

        if viewer_id is not None and feedback.author_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author may update this feedback",
            )

        return await FeedbackRepository.update(self.db, feedback, feedback_in)

    async def delete_feedback(
        self,
        feedback_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> None:
        feedback = await FeedbackRepository.get_by_id(self.db, feedback_id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedback with ID '{feedback_id}' not found",
            )

        if viewer_id is not None and feedback.author_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author may delete this feedback",
            )

        await FeedbackRepository.delete(self.db, feedback)

    @staticmethod
    def _is_feedback_visible_to_viewer(
        feedback: Feedback,
        cycle: Optional[object],
        viewer_id: Optional[uuid.UUID],
        viewer_role: Optional[str],
    ) -> bool:
        # Public / shared feedback is visible to anyone authorized for the cycle
        if feedback.visibility == FeedbackVisibility.SHARED.value:
            return True

        # Administrator can inspect all feedback
        if viewer_role in {"admin", "administrator"}:
            return True

        # Author can always see their own submitted feedback
        if viewer_id is not None and feedback.author_id == viewer_id:
            return True

        # Manager-only visibility: visible to cycle owner / manager
        if feedback.visibility == FeedbackVisibility.MANAGER_ONLY.value:
            if viewer_role == "manager":
                return True
            if cycle is not None and hasattr(cycle, "owner_id") and cycle.owner_id == viewer_id:
                return True

        # Private feedback is only visible to the author and admin (checked above)
        return False

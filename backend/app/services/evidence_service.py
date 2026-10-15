import uuid
from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence, EvidenceAccessPolicy
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.review_cycle_repository import ReviewCycleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate


class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_evidence_by_id(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
    ) -> Evidence:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        cycle = await ReviewCycleRepository.get_by_id(self.db, evidence.cycle_id)

        if not self._is_evidence_accessible_to_viewer(evidence, cycle, viewer_id, viewer_role):
            # PRD Section 11: Return 404 when resource disclosure policy requires hiding existence
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        return evidence

    async def list_evidence(
        self,
        cycle_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Evidence]:
        cycle = None
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

        items = await EvidenceRepository.list_evidence(
            self.db,
            cycle_id=cycle_id,
            employee_id=employee_id,
            source_type=source_type,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )

        # Enforce access policy filtering
        accessible_items = [
            item for item in items if self._is_evidence_accessible_to_viewer(item, cycle, viewer_id, viewer_role)
        ]
        return accessible_items

    async def create_evidence(self, cycle_id: uuid.UUID, evidence_in: EvidenceCreate) -> Evidence:
        cycle = await ReviewCycleRepository.get_by_id(self.db, cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review cycle with ID '{cycle_id}' not found",
            )

        if evidence_in.uploader_id is not None:
            uploader = await UserRepository.get_by_id(self.db, evidence_in.uploader_id)
            if not uploader:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Uploader user with ID '{evidence_in.uploader_id}' not found",
                )

        if evidence_in.employee_id is not None:
            emp = await UserRepository.get_by_id(self.db, evidence_in.employee_id)
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID '{evidence_in.employee_id}' not found",
                )
            if evidence_in.employee_id != cycle.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Employee ID '{evidence_in.employee_id}' does not match review cycle employee ID '{cycle.employee_id}'",
                )

        return await EvidenceRepository.create(self.db, cycle_id, evidence_in)

    async def update_evidence(
        self,
        evidence_id: uuid.UUID,
        evidence_in: EvidenceUpdate,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> Evidence:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        if viewer_id is not None and evidence.uploader_id is not None and evidence.uploader_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the uploader or an authorized reviewer may update this evidence",
            )

        return await EvidenceRepository.update(self.db, evidence, evidence_in)

    async def delete_evidence(
        self,
        evidence_id: uuid.UUID,
        viewer_id: Optional[uuid.UUID] = None,
    ) -> None:
        evidence = await EvidenceRepository.get_by_id(self.db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found",
            )

        if viewer_id is not None and evidence.uploader_id is not None and evidence.uploader_id != viewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the uploader or an authorized reviewer may delete this evidence",
            )

        await EvidenceRepository.delete(self.db, evidence)

    @staticmethod
    def _is_evidence_accessible_to_viewer(
        evidence: Evidence,
        cycle: Optional[object],
        viewer_id: Optional[uuid.UUID],
        viewer_role: Optional[str],
    ) -> bool:
        # Internal evidence is accessible to all cycle participants
        if evidence.access_policy == EvidenceAccessPolicy.INTERNAL.value:
            return True

        # Administrator can inspect all evidence
        if viewer_role in {"admin", "administrator"}:
            return True

        # Uploader can always access their uploaded evidence
        if viewer_id is not None and evidence.uploader_id == viewer_id:
            return True

        # Manager-only / Restricted / Confidential policies
        if viewer_role == "manager":
            return True

        if cycle is not None and hasattr(cycle, "owner_id") and cycle.owner_id == viewer_id:
            return True

        return False

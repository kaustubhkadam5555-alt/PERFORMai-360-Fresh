import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.models.review_cycle import ReviewCycle
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate


class EvidenceRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, evidence_id: uuid.UUID) -> Optional[Evidence]:
        result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
        return result.scalars().first()

    @staticmethod
    async def list_evidence(
        db: AsyncSession,
        cycle_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        source_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        allowed_policies: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Evidence]:
        query = (
            select(Evidence)
            .offset(skip)
            .limit(limit)
            .order_by(Evidence.source_date.desc().nullslast(), Evidence.created_at.desc())
        )
        if employee_id:
            query = query.join(ReviewCycle, Evidence.cycle_id == ReviewCycle.id).where(
                ReviewCycle.employee_id == employee_id
            )
        if cycle_id:
            query = query.where(Evidence.cycle_id == cycle_id)
        if source_type:
            query = query.where(Evidence.source_type == source_type)
        if start_date:
            query = query.where(Evidence.source_date >= start_date)
        if end_date:
            query = query.where(Evidence.source_date <= end_date)
        if allowed_policies is not None:
            query = query.where(Evidence.access_policy.in_(allowed_policies))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, cycle_id: uuid.UUID, evidence_in: EvidenceCreate) -> Evidence:
        evidence = Evidence(
            cycle_id=cycle_id,
            source_type=evidence_in.source_type,
            title=evidence_in.title,
            storage_reference=evidence_in.storage_reference,
            source_date=evidence_in.source_date,
            uploader_id=evidence_in.uploader_id,
            metadata_json=evidence_in.metadata_json or {},
            access_policy=evidence_in.access_policy,
        )
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        return evidence

    @staticmethod
    async def update(db: AsyncSession, db_evidence: Evidence, evidence_in: EvidenceUpdate) -> Evidence:
        update_data = evidence_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_evidence, field, value)
        await db.commit()
        await db.refresh(db_evidence)
        return db_evidence

    @staticmethod
    async def delete(db: AsyncSession, db_evidence: Evidence) -> None:
        await db.delete(db_evidence)
        await db.commit()

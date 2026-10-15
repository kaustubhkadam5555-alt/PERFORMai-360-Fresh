import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bias_flag import BiasFlag
from app.schemas.bias_flag import BiasFlagCreate, BiasFlagUpdate


class BiasFlagRepository:
    """Repository layer for persisting, querying, and updating Bias and Evidence-Quality Flags."""

    @staticmethod
    async def create(db: AsyncSession, flag_in: BiasFlagCreate) -> BiasFlag:
        flag = BiasFlag(
            cycle_id=flag_in.cycle_id,
            flag_type=flag_in.flag_type,
            explanation=flag_in.explanation,
            severity=flag_in.severity,
            evidence_ids=[str(eid) for eid in flag_in.evidence_ids] if flag_in.evidence_ids else [],
            suggested_action=flag_in.suggested_action,
            status=flag_in.status,
            reviewer_comment=flag_in.reviewer_comment,
        )
        db.add(flag)
        await db.commit()
        await db.refresh(flag)
        return flag

    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        flags_data: List[Dict[str, Any]],
    ) -> List[BiasFlag]:
        flags: List[BiasFlag] = []
        for data in flags_data:
            flag = BiasFlag(
                cycle_id=cycle_id,
                flag_type=data["flag_type"],
                explanation=data["explanation"],
                severity=data.get("severity", "review"),
                evidence_ids=[str(eid) for eid in data.get("evidence_ids", [])],
                suggested_action=data.get("suggested_action"),
                status=data.get("status", "open"),
                reviewer_comment=data.get("reviewer_comment"),
            )
            db.add(flag)
            flags.append(flag)
        await db.commit()
        for f in flags:
            await db.refresh(f)
        return flags

    @staticmethod
    async def get_by_id(db: AsyncSession, flag_id: uuid.UUID) -> Optional[BiasFlag]:
        result = await db.execute(select(BiasFlag).where(BiasFlag.id == flag_id))
        return result.scalars().first()

    @staticmethod
    async def list_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        status: Optional[str] = None,
        flag_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[BiasFlag]:
        query = select(BiasFlag).where(BiasFlag.cycle_id == cycle_id)
        if status:
            query = query.where(BiasFlag.status == status)
        if flag_type:
            query = query.where(BiasFlag.flag_type == flag_type)
        if severity:
            query = query.where(BiasFlag.severity == severity)
        query = query.order_by(desc(BiasFlag.created_at))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update(
        db: AsyncSession,
        db_flag: BiasFlag,
        flag_update: BiasFlagUpdate,
    ) -> BiasFlag:
        update_data = flag_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_flag, field, value)
        await db.commit()
        await db.refresh(db_flag)
        return db_flag

    @staticmethod
    async def delete(db: AsyncSession, db_flag: BiasFlag) -> None:
        await db.delete(db_flag)
        await db.commit()

    @staticmethod
    async def clear_open_flags_for_cycle(
        db: AsyncSession,
        cycle_id: uuid.UUID,
        flag_types: Optional[List[str]] = None,
    ) -> int:
        """
        Clears existing 'open' flags before re-running audit rules,
        preserving acknowledged, resolved, or not_applicable flags so reviewer human input is never lost.
        """
        query = delete(BiasFlag).where(
            BiasFlag.cycle_id == cycle_id,
            BiasFlag.status == "open",
        )
        if flag_types:
            query = query.where(BiasFlag.flag_type.in_(flag_types))
        result = await db.execute(query)
        await db.commit()
        return result.rowcount

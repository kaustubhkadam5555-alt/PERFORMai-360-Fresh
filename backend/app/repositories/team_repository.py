import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team, TeamMembership
from app.schemas.team import TeamCreate, TeamMembershipCreate, TeamUpdate


class TeamRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, team_id: uuid.UUID) -> Optional[Team]:
        result = await db.execute(select(Team).where(Team.id == team_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[Team]:
        result = await db.execute(select(Team).where(Team.name == name))
        return result.scalars().first()

    @staticmethod
    async def list_teams(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Team]:
        query = select(Team).offset(skip).limit(limit).order_by(Team.name.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, team_in: TeamCreate) -> Team:
        team = Team(
            name=team_in.name,
            description=team_in.description,
            manager_id=team_in.manager_id,
        )
        db.add(team)
        await db.commit()
        await db.refresh(team)
        return team

    @staticmethod
    async def update(db: AsyncSession, db_team: Team, team_in: TeamUpdate) -> Team:
        update_data = team_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_team, field, value)
        await db.commit()
        await db.refresh(db_team)
        return db_team

    @staticmethod
    async def add_member(db: AsyncSession, team_id: uuid.UUID, member_in: TeamMembershipCreate) -> TeamMembership:
        membership = TeamMembership(
            team_id=team_id,
            user_id=member_in.user_id,
            role_in_team=member_in.role_in_team,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)
        return membership

    @staticmethod
    async def get_membership(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> Optional[TeamMembership]:
        result = await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def list_members(db: AsyncSession, team_id: uuid.UUID) -> List[TeamMembership]:
        result = await db.execute(
            select(TeamMembership).where(TeamMembership.team_id == team_id).order_by(TeamMembership.created_at.asc())
        )
        return list(result.scalars().all())

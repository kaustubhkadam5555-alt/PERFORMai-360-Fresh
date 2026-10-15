import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team, TeamMembership
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.team import TeamCreate, TeamMembershipCreate, TeamUpdate


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_team_by_id(self, team_id: uuid.UUID) -> Team:
        team = await TeamRepository.get_by_id(self.db, team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID '{team_id}' not found",
            )
        return team

    async def list_teams(self, skip: int = 0, limit: int = 100) -> List[Team]:
        return await TeamRepository.list_teams(self.db, skip=skip, limit=limit)

    async def create_team(self, team_in: TeamCreate) -> Team:
        existing = await TeamRepository.get_by_name(self.db, team_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Team with name '{team_in.name}' already exists",
            )
        if team_in.manager_id:
            manager = await UserRepository.get_by_id(self.db, team_in.manager_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Designated manager user ID '{team_in.manager_id}' does not exist",
                )
        return await TeamRepository.create(self.db, team_in)

    async def update_team(self, team_id: uuid.UUID, team_in: TeamUpdate) -> Team:
        team = await self.get_team_by_id(team_id)
        if team_in.name and team_in.name != team.name:
            existing = await TeamRepository.get_by_name(self.db, team_in.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Team with name '{team_in.name}' already exists",
                )
        if team_in.manager_id:
            manager = await UserRepository.get_by_id(self.db, team_in.manager_id)
            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Designated manager user ID '{team_in.manager_id}' does not exist",
                )
        return await TeamRepository.update(self.db, team, team_in)

    async def add_member(self, team_id: uuid.UUID, member_in: TeamMembershipCreate) -> TeamMembership:
        await self.get_team_by_id(team_id)
        user = await UserRepository.get_by_id(self.db, member_in.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{member_in.user_id}' does not exist",
            )
        existing = await TeamRepository.get_membership(self.db, team_id, member_in.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this team",
            )
        return await TeamRepository.add_member(self.db, team_id, member_in)

    async def list_members(self, team_id: uuid.UUID) -> List[TeamMembership]:
        await self.get_team_by_id(team_id)
        return await TeamRepository.list_members(self.db, team_id)

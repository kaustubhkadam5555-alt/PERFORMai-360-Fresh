import uuid
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.team import (
    TeamCreate,
    TeamMembershipCreate,
    TeamMembershipResponse,
    TeamResponse,
)
from app.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=List[TeamResponse], summary="List teams")
async def list_teams(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[TeamResponse]:
    service = TeamService(db)
    return await service.list_teams(skip=skip, limit=limit)


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
)
async def create_team(
    team_in: TeamCreate,
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    service = TeamService(db)
    return await service.create_team(team_in)


@router.get("/{team_id}", response_model=TeamResponse, summary="Get team by ID")
async def get_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    service = TeamService(db)
    return await service.get_team_by_id(team_id)


@router.post(
    "/{team_id}/members",
    response_model=TeamMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to team",
)
async def add_team_member(
    team_id: uuid.UUID,
    member_in: TeamMembershipCreate,
    db: AsyncSession = Depends(get_db),
) -> TeamMembershipResponse:
    service = TeamService(db)
    return await service.add_member(team_id, member_in)


@router.get(
    "/{team_id}/members",
    response_model=List[TeamMembershipResponse],
    summary="List team members",
)
async def list_team_members(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[TeamMembershipResponse]:
    service = TeamService(db)
    return await service.list_members(team_id)

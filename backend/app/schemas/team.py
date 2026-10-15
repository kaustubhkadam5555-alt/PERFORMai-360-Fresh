import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None


class TeamResponse(TeamBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMembershipCreate(BaseModel):
    user_id: uuid.UUID
    role_in_team: str = Field(default="member", max_length=50)


class TeamMembershipResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role_in_team: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

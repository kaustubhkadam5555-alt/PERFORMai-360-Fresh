import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.goal import GoalStatus


class GoalBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000)
    measurable_target: Optional[str] = Field(default=None, max_length=2000)
    status: str = Field(default=GoalStatus.IN_PROGRESS.value)
    due_date: Optional[date] = None
    outcome_notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {s.value for s in GoalStatus}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {sorted(allowed)}")
        return v.lower()


class GoalCreate(GoalBase):
    cycle_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None


class GoalUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    measurable_target: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = None
    due_date: Optional[date] = None
    outcome_notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {s.value for s in GoalStatus}
            if v.lower() not in allowed:
                raise ValueError(f"Invalid status '{v}'. Allowed statuses: {sorted(allowed)}")
            return v.lower()
        return v


class GoalResponse(GoalBase):
    id: uuid.UUID
    cycle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

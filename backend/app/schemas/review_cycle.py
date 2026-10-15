import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewCycleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    employee_id: uuid.UUID
    owner_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    period_start: date
    period_end: date
    template_id: str = Field(default="standard_swe_v1", max_length=100)

    @model_validator(mode="after")
    def validate_period_range(self) -> "ReviewCycleBase":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class ReviewCycleCreate(ReviewCycleBase):
    pass


class ReviewCycleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=50)
    team_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_period_range(self) -> "ReviewCycleUpdate":
        if self.period_start is not None and self.period_end is not None:
            if self.period_end < self.period_start:
                raise ValueError("period_end must be on or after period_start")
        return self


class ReviewCycleResponse(ReviewCycleBase):
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.feedback import FeedbackType, FeedbackVisibility


class FeedbackBase(BaseModel):
    author_id: uuid.UUID
    subject_employee_id: uuid.UUID
    feedback_type: str = Field(default=FeedbackType.PEER.value)
    category: Optional[str] = Field(default=None, max_length=100)
    content: str = Field(..., min_length=1, max_length=10000)
    visibility: str = Field(default=FeedbackVisibility.SHARED.value)

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v: str) -> str:
        allowed = {t.value for t in FeedbackType}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid feedback_type '{v}'. Allowed types: {sorted(allowed)}")
        return v.lower()

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        allowed = {vis.value for vis in FeedbackVisibility}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid visibility '{v}'. Allowed values: {sorted(allowed)}")
        return v.lower()

    @model_validator(mode="after")
    def validate_author_subject_relationship(self) -> "FeedbackBase":
        if self.feedback_type == FeedbackType.SELF.value:
            if self.author_id != self.subject_employee_id:
                raise ValueError("Self feedback must have author_id matching subject_employee_id")
        else:
            if self.author_id == self.subject_employee_id:
                raise ValueError(f"{self.feedback_type.capitalize()} feedback author cannot be the subject employee")
        return self


class FeedbackCreate(FeedbackBase):
    cycle_id: Optional[uuid.UUID] = None


class FeedbackUpdate(BaseModel):
    category: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    visibility: Optional[str] = None

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {vis.value for vis in FeedbackVisibility}
            if v.lower() not in allowed:
                raise ValueError(f"Invalid visibility '{v}'. Allowed values: {sorted(allowed)}")
            return v.lower()
        return v


class FeedbackResponse(FeedbackBase):
    id: uuid.UUID
    cycle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

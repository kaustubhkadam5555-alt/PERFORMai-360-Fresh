import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.evidence import EvidenceAccessPolicy, EvidenceSourceType


class EvidenceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(default=EvidenceSourceType.DOCUMENT.value)
    storage_reference: Optional[str] = Field(default=None, max_length=500)
    source_date: Optional[date] = None
    uploader_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    access_policy: str = Field(default=EvidenceAccessPolicy.INTERNAL.value)

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {t.value for t in EvidenceSourceType}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid source_type '{v}'. Allowed types: {sorted(allowed)}")
        return v.lower()

    @field_validator("access_policy")
    @classmethod
    def validate_access_policy(cls, v: str) -> str:
        allowed = {p.value for p in EvidenceAccessPolicy}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid access_policy '{v}'. Allowed policies: {sorted(allowed)}")
        return v.lower()

    @field_validator("storage_reference")
    @classmethod
    def sanitize_storage_reference(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Prevent directory traversal attacks
            if ".." in v or "\\" in v:
                raise ValueError("storage_reference contains unsafe directory traversal sequences")
            cleaned = re.sub(r"[^a-zA-Z0-9_\-\./]", "", v)
            if ".." in cleaned:
                raise ValueError("storage_reference contains unsafe directory traversal sequences")
            return cleaned
        return v


class EvidenceCreate(EvidenceBase):
    cycle_id: Optional[uuid.UUID] = None
    employee_id: Optional[uuid.UUID] = None


class EvidenceUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    source_type: Optional[str] = None
    storage_reference: Optional[str] = Field(default=None, max_length=500)
    source_date: Optional[date] = None
    metadata_json: Optional[Dict[str, Any]] = None
    access_policy: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {t.value for t in EvidenceSourceType}
            if v.lower() not in allowed:
                raise ValueError(f"Invalid source_type '{v}'. Allowed types: {sorted(allowed)}")
            return v.lower()
        return v

    @field_validator("access_policy")
    @classmethod
    def validate_access_policy(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {p.value for p in EvidenceAccessPolicy}
            if v.lower() not in allowed:
                raise ValueError(f"Invalid access_policy '{v}'. Allowed policies: {sorted(allowed)}")
            return v.lower()
        return v

    @field_validator("storage_reference")
    @classmethod
    def sanitize_storage_reference(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if ".." in v or v.startswith("/") or "\\" in v:
                cleaned = re.sub(r"[^a-zA-Z0-9_\-\./]", "", v).lstrip("/\\")
                if ".." in cleaned:
                    raise ValueError("storage_reference contains unsafe directory traversal sequences")
                return cleaned
        return v


class EvidenceResponse(EvidenceBase):
    id: uuid.UUID
    cycle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceCompletenessResponse(BaseModel):
    cycle_id: uuid.UUID
    employee_id: uuid.UUID
    period_start: date
    period_end: date
    total_evidence_count: int
    source_distribution: Dict[str, int]
    earliest_evidence_date: Optional[date] = None
    latest_evidence_date: Optional[date] = None
    period_span_days: int
    evidence_span_days: int
    detected_gaps: list[str] = Field(default_factory=list)
    has_recency_bias_risk: bool = False
    completeness_score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)

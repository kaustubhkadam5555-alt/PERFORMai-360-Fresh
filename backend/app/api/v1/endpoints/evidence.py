import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.evidence import EvidenceCreate, EvidenceResponse, EvidenceUpdate
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.get("", response_model=List[EvidenceResponse], summary="List evidence records")
async def list_evidence(
    cycle_id: Optional[uuid.UUID] = Query(default=None, description="Filter by review cycle ID"),
    employee_id: Optional[uuid.UUID] = Query(default=None, description="Filter by employee ID"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type"),
    start_date: Optional[date] = Query(default=None, description="Filter by source date start"),
    end_date: Optional[date] = Query(default=None, description="Filter by source date end"),
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for access checks"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[EvidenceResponse]:
    service = EvidenceService(db)
    return await service.list_evidence(
        cycle_id=cycle_id,
        employee_id=employee_id,
        source_type=source_type,
        start_date=start_date,
        end_date=end_date,
        viewer_id=viewer_id or x_viewer_id,
        viewer_role=viewer_role or x_viewer_role,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register evidence",
)
async def register_evidence(
    evidence_in: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    if not evidence_in.cycle_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="cycle_id must be provided in request body when registering evidence via /evidence",
        )
    service = EvidenceService(db)
    return await service.create_evidence(cycle_id=evidence_in.cycle_id, evidence_in=evidence_in)


@router.get("/{evidence_id}", response_model=EvidenceResponse, summary="Get evidence by ID")
async def get_evidence(
    evidence_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    service = EvidenceService(db)
    return await service.get_evidence_by_id(
        evidence_id, viewer_id=viewer_id or x_viewer_id, viewer_role=viewer_role or x_viewer_role
    )


@router.patch("/{evidence_id}", response_model=EvidenceResponse, summary="Update evidence")
async def update_evidence(
    evidence_id: uuid.UUID,
    evidence_in: EvidenceUpdate,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    db: AsyncSession = Depends(get_db),
) -> EvidenceResponse:
    service = EvidenceService(db)
    return await service.update_evidence(evidence_id, evidence_in, viewer_id=viewer_id or x_viewer_id)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete evidence")
async def delete_evidence(
    evidence_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = EvidenceService(db)
    await service.delete_evidence(evidence_id, viewer_id=viewer_id or x_viewer_id)

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_governance import (
    ApprovalHistoryResponse,
    GovernanceAuditListResponse,
    ReportApprovalRequest,
    ReportDetailResponse,
    ReportRevisionRequest,
    ReportVersionDetail,
    ReportVersionListResponse,
    SectionEditRequest,
    VersionComparisonResponse,
)
from app.services.report_export_service import ReportExportService
from app.services.report_governance_service import ReportGovernanceService

router = APIRouter(tags=["reports"])


# ---------------------------------------------------------------------------
# Report Retrieval Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}",
    response_model=ReportDetailResponse,
    summary="Get report details by report ID",
    description="Retrieves the current draft or approved review report with full structured content, version number, and approval status.",
)
async def get_report_by_id(
    report_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator, employee)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.get_report_by_id(
        report_id=report_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/review-cycles/{cycle_id}/report",
    response_model=ReportDetailResponse,
    summary="Get report details by review cycle ID",
    description="Retrieves the active or finalized review report for a specific review cycle.",
)
async def get_report_by_cycle(
    cycle_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator, employee)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.get_report_for_cycle(
        cycle_id=cycle_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


# ---------------------------------------------------------------------------
# Feature A: Section-Level Report Editing
# ---------------------------------------------------------------------------


@router.post(
    "/reports/{report_id}/sections/{section_key}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit an individual report section",
    description=(
        "Updates permitted report section with optimistic concurrency control (base_version_number). "
        "Increments the version number, creates an immutable ReportVersion snapshot, "
        "protects previously approved historical versions, and records a governance audit event."
    ),
)
@router.post(
    "/reports/{report_id}/sections/{section_key}/edits",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit an individual report section (alias endpoint)",
    include_in_schema=False,
)
async def edit_report_section(
    report_id: uuid.UUID,
    section_key: str,
    request_in: SectionEditRequest,
    viewer_id: Optional[uuid.UUID] = Query(default=None, description="Caller user ID for authorization"),
    viewer_role: Optional[str] = Query(default=None, description="Caller role (manager, administrator)"),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_editor_id = viewer_id or x_viewer_id
    effective_editor_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.edit_section(
        report_id=report_id,
        section_key=section_key,
        request_in=request_in,
        editor_id=effective_editor_id,
        editor_role=effective_editor_role,
    )


# ---------------------------------------------------------------------------
# Feature B: Version Listing & History
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}/versions",
    response_model=ReportVersionListResponse,
    summary="List all historical immutable versions of a report",
    description="Returns chronological metadata for all snapshots recorded for the given report.",
)
async def list_report_versions(
    report_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200, description="Max versions to return"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportVersionListResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.list_versions(
        report_id=report_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        limit=limit,
    )


@router.get(
    "/reports/{report_id}/versions/{version_id_or_number}",
    response_model=ReportVersionDetail,
    summary="Get exact historical snapshot of a report version",
    description="Retrieves the exact, immutable structured content and metadata for a specific version by version number or UUID.",
)
async def get_report_version(
    report_id: uuid.UUID,
    version_id_or_number: str,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportVersionDetail:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.get_version(
        report_id=report_id,
        version_identifier=version_id_or_number,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


# ---------------------------------------------------------------------------
# Feature C: Version Comparison
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}/compare",
    response_model=VersionComparisonResponse,
    summary="Compare two versions of a report deterministically",
    description=(
        "Computes a deterministic, transparent diff between any two versions of the same report. "
        "Provides unified text diffs for prose and additions/removals for structured lists and citations."
    ),
)
async def compare_report_versions(
    report_id: uuid.UUID,
    from_version: Optional[str] = Query(default=None, alias="from_version", description="Base version number or UUID"),
    to_version: Optional[str] = Query(default=None, alias="to_version", description="Target version number or UUID"),
    from_alias: Optional[str] = Query(default=None, alias="from", description="Base version alias"),
    to_alias: Optional[str] = Query(default=None, alias="to", description="Target version alias"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> VersionComparisonResponse:
    effective_from = from_version or from_alias
    effective_to = to_version or to_alias

    if not effective_from or not effective_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Both 'from_version' (or 'from') and 'to_version' (or 'to') query parameters are required.",
        )

    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.compare_versions(
        report_id=report_id,
        from_version_identifier=effective_from,
        to_version_identifier=effective_to,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


# ---------------------------------------------------------------------------
# Feature D & E: Human Approval and Revision Request
# ---------------------------------------------------------------------------


@router.post(
    "/reports/{report_id}/approve",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve and finalize an exact report version",
    description=(
        "Deliberate human approval bound to an exact version ID and version number. "
        "Rejects stale approvals (HTTP 409) if the report has advanced. "
        "Transitions report status to 'approved', freezes the version snapshot, records an Approval entry, "
        "and completes any active workflow runs."
    ),
)
async def approve_report(
    report_id: uuid.UUID,
    request_in: Optional[ReportApprovalRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_reviewer_id = viewer_id or x_viewer_id
    effective_reviewer_role = viewer_role or x_viewer_role

    if not effective_reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer identity is required for approval.",
        )

    req = request_in or ReportApprovalRequest()
    service = ReportGovernanceService(db)
    return await service.approve_report(
        report_id=report_id,
        request_in=req,
        reviewer_id=effective_reviewer_id,
        reviewer_role=effective_reviewer_role or "manager",
    )


@router.post(
    "/reports/{report_id}/versions/{version_id}/approve",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve an exact report version by version ID (alias endpoint)",
    include_in_schema=True,
)
async def approve_report_version(
    report_id: uuid.UUID,
    version_id: uuid.UUID,
    request_in: Optional[ReportApprovalRequest] = None,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_reviewer_id = viewer_id or x_viewer_id
    effective_reviewer_role = viewer_role or x_viewer_role

    if not effective_reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer identity is required for approval.",
        )

    req = request_in.model_copy() if request_in else ReportApprovalRequest()
    req.version_id = version_id

    service = ReportGovernanceService(db)
    return await service.approve_report(
        report_id=report_id,
        request_in=req,
        reviewer_id=effective_reviewer_id,
        reviewer_role=effective_reviewer_role or "manager",
    )


@router.post(
    "/reports/{report_id}/request-revision",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Request revisions on a report draft",
    description="Transitions report to 'revision_requested' with mandatory reviewer instructions and governance audit logging.",
)
async def request_report_revision(
    report_id: uuid.UUID,
    request_in: ReportRevisionRequest,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ReportDetailResponse:
    effective_reviewer_id = viewer_id or x_viewer_id
    effective_reviewer_role = viewer_role or x_viewer_role

    if not effective_reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer identity is required to request revisions.",
        )

    service = ReportGovernanceService(db)
    return await service.request_revision(
        report_id=report_id,
        request_in=request_in,
        reviewer_id=effective_reviewer_id,
        reviewer_role=effective_reviewer_role or "manager",
    )


# ---------------------------------------------------------------------------
# Feature F: Approval History & Governance Audit Trail
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}/approvals",
    response_model=ApprovalHistoryResponse,
    summary="Get human approval and sign-off history",
    description="Returns all approval and revision records associated with this report.",
)
async def get_report_approvals(
    report_id: uuid.UUID,
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> ApprovalHistoryResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.get_approval_history(
        report_id=report_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )


@router.get(
    "/reports/{report_id}/audit-events",
    response_model=GovernanceAuditListResponse,
    summary="Get traceable governance audit events for a report",
    description="Returns chronological audit logs for section edits, version creations, approvals, and revisions.",
)
async def get_report_audit_events(
    report_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500, description="Max audit events to return"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> GovernanceAuditListResponse:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportGovernanceService(db)
    return await service.get_audit_history(
        report_id=report_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Phase 9: PDF & DOCX Export Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}/export/pdf",
    summary="Export review report as professional PDF",
    description=(
        "Generates a downloadable, branded PDF performance review document with exact version identification, "
        "human manager approval metadata, structured strengths and citations, growth opportunities, and goals."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Downloadable binary PDF document",
        }
    },
)
async def export_report_pdf(
    report_id: uuid.UUID,
    version_number: Optional[int] = Query(default=None, description="Specific version number to export"),
    version_id: Optional[uuid.UUID] = Query(default=None, description="Specific version ID to export"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportExportService(db)
    pdf_bytes, filename = await service.generate_pdf(
        report_id=report_id,
        version_number=version_number,
        version_id=version_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get(
    "/reports/{report_id}/export/docx",
    summary="Export review report as professional Word DOCX document",
    description=(
        "Generates a downloadable, styled Microsoft Word DOCX document with version snapshot identification, "
        "metadata tables, human approval sign-off details, and evidence citations."
    ),
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}},
            "description": "Downloadable binary DOCX document",
        }
    },
)
async def export_report_docx(
    report_id: uuid.UUID,
    version_number: Optional[int] = Query(default=None, description="Specific version number to export"),
    version_id: Optional[uuid.UUID] = Query(default=None, description="Specific version ID to export"),
    viewer_id: Optional[uuid.UUID] = Query(default=None),
    viewer_role: Optional[str] = Query(default=None),
    x_viewer_id: Optional[uuid.UUID] = Header(default=None, alias="X-Viewer-Id"),
    x_viewer_role: Optional[str] = Header(default=None, alias="X-Viewer-Role"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    effective_viewer_id = viewer_id or x_viewer_id
    effective_viewer_role = viewer_role or x_viewer_role
    service = ReportExportService(db)
    docx_bytes, filename = await service.generate_docx(
        report_id=report_id,
        version_number=version_number,
        version_id=version_id,
        viewer_id=effective_viewer_id,
        viewer_role=effective_viewer_role,
    )
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    )

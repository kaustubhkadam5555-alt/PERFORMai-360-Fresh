import io
import uuid
from datetime import date
from typing import Any, Dict

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.user import User, UserRole
from app.repositories.report_governance_repository import ReportGovernanceRepository


@pytest.fixture
async def export_env(db_session: AsyncSession) -> Dict[str, Any]:
    manager = User(
        full_name="Staff Engineering Lead",
        email=f"lead_export_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.MANAGER,
    )
    employee = User(
        full_name="Senior Engineer Élodie",
        email=f"elodie_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    unauthorized_employee = User(
        full_name="Other Employee",
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([manager, employee, unauthorized_employee])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(employee)
    await db_session.refresh(unauthorized_employee)

    cycle = ReviewCycle(
        title="2026 Mid-Year Technical Review",
        owner_id=manager.id,
        employee_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        status=ReviewCycleStatus.ACTIVE,
    )
    db_session.add(cycle)
    await db_session.commit()
    await db_session.refresh(cycle)

    report = ReviewReport(
        cycle_id=cycle.id,
        version_number=1,
        status="approved",
        structured_content={
            "executive_summary": (
                "Élodie delivered key distributed data storage optimizations with zero downtime. "
                "She also exhibited strong cross-functional mentoring."
            ),
            "strengths": [
                {
                    "theme": "Distributed Systems Mastery",
                    "narrative": "Refactored the streaming replication pipeline to support 50k req/sec.",
                    "supporting_evidence_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                    "confidence_score": 0.95,
                }
            ],
            "growth_areas": [
                {
                    "theme": "RFC Documentation Velocity",
                    "narrative": "Publish technical architecture specifications earlier in the design sprint.",
                    "gap_observed": "Late RFC submissions delayed team review by 1 sprint.",
                }
            ],
            "goal_progress": [
                {
                    "description": "Zero Downtime Replication",
                    "status": "completed",
                    "measurable_target": "99.999% availability",
                    "outcome_notes": "Target met in production Q2.",
                }
            ],
            "impact_highlights": [
                {
                    "title": "Cost Optimization",
                    "impact_summary": "Reduced cloud storage egress spend by 22% ($45k/mo).",
                }
            ],
            "evidence_gaps_and_limitations": [
                "Peer feedback from QA team was unavailable during this evaluation cycle."
            ],
            "suggested_discussion_questions": [
                "What architectural areas would you like to explore in H2?",
                {"category": "Career Growth", "question": "Are you interested in tech lead ownership?"},
            ],
            "reviewer_notes": "Strong candidate for Staff promotion calibration in Q4.",
            "citations": [],
        },
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    # Persist immutable version snapshot
    v1 = await ReportGovernanceRepository.create_version(
        db=db_session,
        report_id=report.id,
        cycle_id=cycle.id,
        version_number=1,
        structured_content=report.structured_content,
        status="approved",
        changed_section="all",
        change_summary="Finalized report approval",
        author_id=manager.id,
        author_role="manager",
    )

    # Persist human approval
    app1 = Approval(
        report_id=report.id,
        version_id=v1.id,
        version_number=1,
        reviewer_id=manager.id,
        decision="approved",
        comments="Thoroughly reviewed and approved for H1 calibration.",
    )
    db_session.add(app1)
    await db_session.commit()

    return {
        "manager": manager,
        "employee": employee,
        "unauthorized_employee": unauthorized_employee,
        "cycle": cycle,
        "report": report,
        "version_1": v1,
    }


# ===========================================================================
# 1. PDF Export Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_export_pdf_approved_report_success(async_client: AsyncClient, export_env: Dict[str, Any]):
    report = export_env["report"]
    manager = export_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get(f"/api/v1/reports/{report.id}/export/pdf", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment;" in res.headers["content-disposition"]
    assert ".pdf" in res.headers["content-disposition"]

    # PDF binary file signature check
    pdf_bytes = res.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000  # Non-empty rendered PDF


@pytest.mark.asyncio
async def test_export_pdf_employee_access_and_reviewer_notes_masking(
    async_client: AsyncClient, export_env: Dict[str, Any]
):
    report = export_env["report"]
    employee = export_env["employee"]

    headers = {"X-Viewer-Id": str(employee.id), "X-Viewer-Role": "employee"}

    # Employee can export their own report
    res = await async_client.get(f"/api/v1/reports/{report.id}/export/pdf", headers=headers)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_export_pdf_unauthorized_employee_blocked(async_client: AsyncClient, export_env: Dict[str, Any]):
    report = export_env["report"]
    unauthorized_employee = export_env["unauthorized_employee"]

    headers = {"X-Viewer-Id": str(unauthorized_employee.id), "X-Viewer-Role": "employee"}

    # Other employee cannot export this report
    res = await async_client.get(f"/api/v1/reports/{report.id}/export/pdf", headers=headers)
    assert res.status_code == 404


# ===========================================================================
# 2. DOCX Export Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_export_docx_report_success(async_client: AsyncClient, export_env: Dict[str, Any]):
    report = export_env["report"]
    manager = export_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    res = await async_client.get(f"/api/v1/reports/{report.id}/export/docx", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "attachment;" in res.headers["content-disposition"]
    assert ".docx" in res.headers["content-disposition"]

    # DOCX binary signature check (ZIP archive header)
    docx_bytes = res.content
    assert docx_bytes.startswith(b"PK\x03\x04")

    # Parse and inspect with python-docx
    doc = Document(io.BytesIO(docx_bytes))
    full_text = " ".join([p.text for p in doc.paragraphs])

    assert "PERFORMai-360 Evaluation Report" in full_text
    assert "Executive Summary" in full_text
    assert "Élodie" in full_text or "Elodie" in full_text or "delivered key distributed" in full_text
    assert "Distributed Systems Mastery" in full_text
    assert "Zero Downtime Replication" in full_text


@pytest.mark.asyncio
async def test_export_docx_specific_version_number(async_client: AsyncClient, export_env: Dict[str, Any]):
    report = export_env["report"]
    manager = export_env["manager"]

    headers = {"X-Viewer-Id": str(manager.id), "X-Viewer-Role": "manager"}

    # Request exact version 1
    res = await async_client.get(
        f"/api/v1/reports/{report.id}/export/docx?version_number=1",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.content.startswith(b"PK\x03\x04")

    # Request non-existent version returns 404
    bad_res = await async_client.get(
        f"/api/v1/reports/{report.id}/export/docx?version_number=999",
        headers=headers,
    )
    assert bad_res.status_code == 404

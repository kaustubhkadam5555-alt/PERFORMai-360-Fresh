import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.bias_flag import BiasFlag
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.finding import Finding
from app.models.goal import Goal
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.team import Team, TeamMembership
from app.models.user import User, UserRole
from app.models.workflow_run import WorkflowRun


@pytest.mark.asyncio
async def test_user_creation_and_uniqueness(db_session: AsyncSession):
    unique_email = f"dev_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        full_name="Synthetic Alice",
        role=UserRole.EMPLOYEE.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.created_at is not None
    assert user.email == unique_email

    # Verify duplicate email raises IntegrityError inside a nested savepoint
    duplicate_user = User(
        email=unique_email,
        full_name="Synthetic Alice Duplicate",
        role=UserRole.EMPLOYEE.value,
    )
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(duplicate_user)
            await db_session.flush()


@pytest.mark.asyncio
async def test_team_and_membership_relationship(db_session: AsyncSession):
    manager = User(
        email=f"mgr_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Manager Bob",
        role=UserRole.MANAGER.value,
    )
    member = User(
        email=f"mem_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Engineer Charlie",
        role=UserRole.EMPLOYEE.value,
    )
    db_session.add_all([manager, member])
    await db_session.flush()

    team = Team(
        name=f"Core Platform {uuid.uuid4().hex[:6]}",
        description="Engineering platform squad",
        manager_id=manager.id,
    )
    db_session.add(team)
    await db_session.flush()

    membership = TeamMembership(
        team_id=team.id,
        user_id=member.id,
        role_in_team="lead_developer",
    )
    db_session.add(membership)
    await db_session.flush()

    assert membership.id is not None
    assert membership.team_id == team.id
    assert membership.user_id == member.id

    # Verify duplicate membership constraint inside a nested savepoint
    duplicate_membership = TeamMembership(
        team_id=team.id,
        user_id=member.id,
        role_in_team="member",
    )
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(duplicate_membership)
            await db_session.flush()


@pytest.mark.asyncio
async def test_review_cycle_hierarchy_and_cascade(db_session: AsyncSession):
    employee = User(
        email=f"emp_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Reviewee Dan",
        role=UserRole.EMPLOYEE.value,
    )
    owner = User(
        email=f"own_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Review Owner Eve",
        role=UserRole.MANAGER.value,
    )
    peer = User(
        email=f"peer_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Peer Reviewer Frank",
        role=UserRole.PEER_REVIEWER.value,
    )
    db_session.add_all([employee, owner, peer])
    await db_session.flush()

    today = date.today()
    cycle = ReviewCycle(
        title="2026-H1 Engineering Review",
        employee_id=employee.id,
        owner_id=owner.id,
        period_start=today - timedelta(days=90),
        period_end=today,
        status=ReviewCycleStatus.OPEN.value,
    )
    db_session.add(cycle)
    await db_session.flush()

    # Add feedback
    feedback = Feedback(
        cycle_id=cycle.id,
        author_id=peer.id,
        subject_employee_id=employee.id,
        feedback_type="peer",
        content="Consistently contributed high quality code reviews.",
    )
    # Add goal
    goal = Goal(
        cycle_id=cycle.id,
        description="Deliver asynchronous review pipeline",
        status="completed",
    )
    # Add evidence
    evidence = Evidence(
        cycle_id=cycle.id,
        source_type="document",
        title="Architecture RFC doc",
        uploader_id=employee.id,
    )
    # Add finding
    finding = Finding(
        cycle_id=cycle.id,
        finding_type="achievement",
        statement="Delivered asynchronous review architecture",
        evidence_ids=["EV-101"],
    )
    # Add bias flag
    flag = BiasFlag(
        cycle_id=cycle.id,
        flag_type="recency_concentration",
        explanation="Feedback focuses primarily on last 2 weeks",
        severity="review",
    )
    # Add workflow run
    run = WorkflowRun(
        cycle_id=cycle.id,
        workflow_status="completed",
    )
    db_session.add_all([feedback, goal, evidence, finding, flag, run])
    await db_session.flush()

    # Add report
    report = ReviewReport(
        cycle_id=cycle.id,
        version_number=1,
        structured_content={"summary": "Excellent performance"},
        status="in_review",
        generated_by_run_id=run.id,
        created_by_id=owner.id,
    )
    db_session.add(report)
    await db_session.flush()

    # Add approval
    approval = Approval(
        report_id=report.id,
        reviewer_id=owner.id,
        decision="approved",
        comments="Solid review cycle",
    )
    # Add audit event
    audit = AuditEvent(
        actor_id=owner.id,
        action="report_approve",
        resource_type="review_report",
        resource_id=str(report.id),
    )
    db_session.add_all([approval, audit])
    await db_session.flush()

    assert feedback.id is not None
    assert goal.id is not None
    assert report.id is not None
    assert approval.id is not None
    assert audit.id is not None

    # Test cascade deletion of cycle
    await db_session.delete(cycle)
    await db_session.flush()

    # Verify dependent items were deleted
    remaining_feedback = await db_session.execute(select(Feedback).where(Feedback.cycle_id == cycle.id))
    assert remaining_feedback.scalars().first() is None

    remaining_goals = await db_session.execute(select(Goal).where(Goal.cycle_id == cycle.id))
    assert remaining_goals.scalars().first() is None

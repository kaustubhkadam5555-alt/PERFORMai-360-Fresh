import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import Approval
from app.models.bias_flag import BiasFlag
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.goal import Goal
from app.models.review_cycle import ReviewCycle, ReviewCycleStatus
from app.models.review_report import ReviewReport
from app.models.workflow_run import WorkflowRun


class AnalyticsRepository:
    """
    Clean, aggregate SQL queries for Phase 9 Analytics.
    Optimized to eliminate N+1 queries through SQL GROUP BY aggregations.
    Strictly enforces employee, team, and date-range scoping.
    """

    @staticmethod
    def _apply_cycle_scope(
        query: Any,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Any:
        role_lower = (viewer_role or "employee").lower()
        if role_lower == "employee" and viewer_id:
            query = query.where(ReviewCycle.employee_id == viewer_id)
        elif role_lower == "manager" and viewer_id:
            query = query.where(ReviewCycle.owner_id == viewer_id)

        if team_id:
            query = query.where(ReviewCycle.team_id == team_id)

        if start_date:
            query = query.where(ReviewCycle.period_start >= start_date)

        if end_date:
            query = query.where(ReviewCycle.period_end <= end_date)

        return query

    @classmethod
    async def get_overview(
        cls,
        db: AsyncSession,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        # 1. Total Cycles and Cycles by Status
        cycle_query = select(ReviewCycle.status, func.count(ReviewCycle.id)).group_by(ReviewCycle.status)
        cycle_query = cls._apply_cycle_scope(cycle_query, viewer_id, viewer_role, team_id, start_date, end_date)
        cycle_res = await db.execute(cycle_query)
        cycles_by_status: Dict[str, int] = {str(status_val): count for status_val, count in cycle_res.all()}
        total_cycles = sum(cycles_by_status.values())

        # 2. Total Reports and Reports by Status
        rep_query = (
            select(ReviewReport.status, func.count(ReviewReport.id))
            .join(ReviewCycle, ReviewReport.cycle_id == ReviewCycle.id)
            .group_by(ReviewReport.status)
        )
        rep_query = cls._apply_cycle_scope(rep_query, viewer_id, viewer_role, team_id, start_date, end_date)
        rep_res = await db.execute(rep_query)
        reports_by_status: Dict[str, int] = {str(status_val): count for status_val, count in rep_res.all()}
        total_reports = sum(reports_by_status.values())

        # 3. Evidence Count
        evi_query = select(func.count(Evidence.id)).join(ReviewCycle, Evidence.cycle_id == ReviewCycle.id)
        evi_query = cls._apply_cycle_scope(evi_query, viewer_id, viewer_role, team_id, start_date, end_date)
        total_evidence = (await db.execute(evi_query)).scalar() or 0

        # 4. Feedback Count
        fb_query = select(func.count(Feedback.id)).join(ReviewCycle, Feedback.cycle_id == ReviewCycle.id)
        fb_query = cls._apply_cycle_scope(fb_query, viewer_id, viewer_role, team_id, start_date, end_date)
        total_feedback = (await db.execute(fb_query)).scalar() or 0

        # 5. Goals Count
        goal_query = select(func.count(Goal.id)).join(ReviewCycle, Goal.cycle_id == ReviewCycle.id)
        goal_query = cls._apply_cycle_scope(goal_query, viewer_id, viewer_role, team_id, start_date, end_date)
        total_goals = (await db.execute(goal_query)).scalar() or 0

        # 6. Approvals Count by Decision
        app_query = (
            select(Approval.decision, func.count(Approval.id))
            .join(ReviewReport, Approval.report_id == ReviewReport.id)
            .join(ReviewCycle, ReviewReport.cycle_id == ReviewCycle.id)
            .group_by(Approval.decision)
        )
        app_query = cls._apply_cycle_scope(app_query, viewer_id, viewer_role, team_id, start_date, end_date)
        app_res = await db.execute(app_query)
        approvals_by_decision: Dict[str, int] = {str(dec): count for dec, count in app_res.all()}
        total_approvals = sum(approvals_by_decision.values())

        # 7. Total Bias Flags
        flag_query = select(func.count(BiasFlag.id)).join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
        flag_query = cls._apply_cycle_scope(flag_query, viewer_id, viewer_role, team_id, start_date, end_date)
        total_bias_flags = (await db.execute(flag_query)).scalar() or 0

        # 8. Average Audit Health Score (from workflow run stage_state)
        wf_query = select(WorkflowRun.stage_state).join(ReviewCycle, WorkflowRun.cycle_id == ReviewCycle.id)
        wf_query = cls._apply_cycle_scope(wf_query, viewer_id, viewer_role, team_id, start_date, end_date)
        raw_states = (await db.execute(wf_query)).scalars().all()
        scores = [
            float(st["audit_health_score"])
            for st in raw_states
            if isinstance(st, dict) and st.get("audit_health_score") is not None
        ]
        average_health_score = round(sum(scores) / len(scores), 1) if scores else None

        # 9. Review Completion Rate:
        # Numerator: cycles marked as COMPLETED, FINALIZED, or APPROVED (or with approved report)
        completed_cycles = sum(
            cycles_by_status.get(s, 0)
            for s in [
                ReviewCycleStatus.COMPLETED.value,
                ReviewCycleStatus.FINALIZED.value,
                ReviewCycleStatus.APPROVED.value,
            ]
        )
        approved_reports_count = reports_by_status.get("approved", 0)
        numerator = max(completed_cycles, approved_reports_count)
        denominator = total_cycles
        completion_rate = round((numerator / denominator * 100.0), 1) if denominator > 0 else 0.0

        return {
            "total_cycles": total_cycles,
            "cycles_by_status": cycles_by_status,
            "total_reports": total_reports,
            "reports_by_status": reports_by_status,
            "completion_rate": completion_rate,
            "completion_numerator": numerator,
            "completion_denominator": denominator,
            "completion_definition": (
                "Percentage of review cycles that have completed reviews with finalized approvals"
            ),
            "total_evidence_items": total_evidence,
            "total_feedback_items": total_feedback,
            "total_goals": total_goals,
            "total_approvals": total_approvals,
            "approvals_by_decision": approvals_by_decision,
            "average_audit_health_score": average_health_score,
            "total_bias_flags": total_bias_flags,
        }

    @classmethod
    async def get_reviews(
        cls,
        db: AsyncSession,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        # Query cycles with employee and latest report relationships
        query = select(ReviewCycle).options(
            selectinload(ReviewCycle.employee),
            selectinload(ReviewCycle.reports),
            selectinload(ReviewCycle.evidence_items),
            selectinload(ReviewCycle.feedback_items),
            selectinload(ReviewCycle.workflow_runs),
        )
        query = cls._apply_cycle_scope(query, viewer_id, viewer_role, team_id, start_date, end_date)
        cycles = (await db.execute(query)).scalars().all()

        total = len(cycles)
        status_dist: Dict[str, int] = {}
        completed_count = 0
        in_progress_count = 0
        total_duration_days = 0
        durations_measured = 0

        cycle_items: List[Dict[str, Any]] = []

        for c in cycles:
            status_dist[c.status] = status_dist.get(c.status, 0) + 1
            is_completed = c.status in {
                ReviewCycleStatus.COMPLETED.value,
                ReviewCycleStatus.FINALIZED.value,
                ReviewCycleStatus.APPROVED.value,
            }
            if is_completed:
                completed_count += 1
            else:
                in_progress_count += 1

            if c.period_start and c.period_end:
                duration = (c.period_end - c.period_start).days
                if duration > 0:
                    total_duration_days += duration
                    durations_measured += 1

            latest_report = c.reports[-1] if c.reports else None
            latest_wf = c.workflow_runs[-1] if c.workflow_runs else None

            cycle_items.append(
                {
                    "cycle_id": c.id,
                    "title": c.title,
                    "employee_name": c.employee.full_name if c.employee else None,
                    "status": c.status,
                    "evidence_count": len(c.evidence_items),
                    "feedback_count": len(c.feedback_items),
                    "report_version": latest_report.version_number if latest_report else None,
                    "report_status": latest_report.status if latest_report else None,
                    "audit_health_score": (
                        float((latest_wf.stage_state or {}).get("audit_health_score"))
                        if latest_wf and (latest_wf.stage_state or {}).get("audit_health_score") is not None
                        else None
                    ),
                }
            )

        avg_duration = round(total_duration_days / durations_measured, 1) if durations_measured > 0 else None
        completion_rate = round((completed_count / total * 100.0), 1) if total > 0 else 0.0

        return {
            "total_cycles": total,
            "status_distribution": status_dist,
            "completed_count": completed_count,
            "in_progress_count": in_progress_count,
            "completion_rate": completion_rate,
            "average_duration_days": avg_duration,
            "cycles": cycle_items,
        }

    @classmethod
    async def get_evidence_analytics(
        cls,
        db: AsyncSession,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        # Evidence source type distribution
        src_query = (
            select(Evidence.source_type, func.count(Evidence.id))
            .join(ReviewCycle, Evidence.cycle_id == ReviewCycle.id)
            .group_by(Evidence.source_type)
        )
        src_query = cls._apply_cycle_scope(src_query, viewer_id, viewer_role, team_id, start_date, end_date)
        src_res = await db.execute(src_query)
        source_dist: Dict[str, int] = {str(k): count for k, count in src_res.all()}
        total_evidence = sum(source_dist.values())

        # Access policy distribution
        pol_query = (
            select(Evidence.access_policy, func.count(Evidence.id))
            .join(ReviewCycle, Evidence.cycle_id == ReviewCycle.id)
            .group_by(Evidence.access_policy)
        )
        pol_query = cls._apply_cycle_scope(pol_query, viewer_id, viewer_role, team_id, start_date, end_date)
        pol_res = await db.execute(pol_query)
        policy_dist: Dict[str, int] = {str(k): count for k, count in pol_res.all()}

        # Citations in reports
        rep_query = select(ReviewReport).join(ReviewCycle, ReviewReport.cycle_id == ReviewCycle.id)
        rep_query = cls._apply_cycle_scope(rep_query, viewer_id, viewer_role, team_id, start_date, end_date)
        reports = (await db.execute(rep_query)).scalars().all()

        cited_evidence_ids = set()
        for r in reports:
            if r.structured_content:
                citations = r.structured_content.get("citations", [])
                for cid in citations:
                    cited_evidence_ids.add(str(cid))

        # Ungrounded claims count from bias flags
        flag_query = (
            select(func.count(BiasFlag.id))
            .join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
            .where(BiasFlag.flag_type == "ungrounded_claim")
        )
        flag_query = cls._apply_cycle_scope(flag_query, viewer_id, viewer_role, team_id, start_date, end_date)
        ungrounded_count = (await db.execute(flag_query)).scalar() or 0

        total_citations = len(cited_evidence_ids)
        supported_claims = max(0, total_citations - ungrounded_count)
        coverage_pct = round((total_citations / total_evidence * 100.0), 1) if total_evidence > 0 else 0.0

        return {
            "total_evidence_items": total_evidence,
            "source_type_distribution": source_dist,
            "access_policy_distribution": policy_dist,
            "total_citations_in_reports": total_citations,
            "supported_claims_count": supported_claims,
            "ungrounded_claims_flag_count": ungrounded_count,
            "overall_coverage_percentage": coverage_pct,
        }

    @classmethod
    async def get_audit_analytics(
        cls,
        db: AsyncSession,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        team_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        # Bias flags by rule
        rule_query = (
            select(BiasFlag.flag_type, func.count(BiasFlag.id))
            .join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
            .group_by(BiasFlag.flag_type)
        )
        rule_query = cls._apply_cycle_scope(rule_query, viewer_id, viewer_role, team_id, start_date, end_date)
        rule_res = await db.execute(rule_query)
        flags_by_rule: Dict[str, int] = {str(k): count for k, count in rule_res.all()}
        total_flags = sum(flags_by_rule.values())

        # Flags by severity
        sev_query = (
            select(BiasFlag.severity, func.count(BiasFlag.id))
            .join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
            .group_by(BiasFlag.severity)
        )
        sev_query = cls._apply_cycle_scope(sev_query, viewer_id, viewer_role, team_id, start_date, end_date)
        sev_res = await db.execute(sev_query)
        flags_by_severity: Dict[str, int] = {str(k): count for k, count in sev_res.all()}

        # Flags by status
        stat_query = (
            select(BiasFlag.status, func.count(BiasFlag.id))
            .join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
            .group_by(BiasFlag.status)
        )
        stat_query = cls._apply_cycle_scope(stat_query, viewer_id, viewer_role, team_id, start_date, end_date)
        stat_res = await db.execute(stat_query)
        flags_by_status: Dict[str, int] = {str(k): count for k, count in stat_res.all()}

        # Workflow run scores distribution from stage_state
        wf_query = select(WorkflowRun.stage_state).join(ReviewCycle, WorkflowRun.cycle_id == ReviewCycle.id)
        wf_query = cls._apply_cycle_scope(wf_query, viewer_id, viewer_role, team_id, start_date, end_date)
        raw_states = (await db.execute(wf_query)).scalars().all()
        scores = [
            float(st["audit_health_score"])
            for st in raw_states
            if isinstance(st, dict) and st.get("audit_health_score") is not None
        ]

        score_dist = {"90-100": 0, "75-89": 0, "50-74": 0, "<50": 0}
        total_score_sum = 0.0

        for sc in scores:
            val = float(sc)
            total_score_sum += val
            if val >= 90:
                score_dist["90-100"] += 1
            elif val >= 75:
                score_dist["75-89"] += 1
            elif val >= 50:
                score_dist["50-74"] += 1
            else:
                score_dist["<50"] += 1

        avg_score = round(total_score_sum / len(scores), 1) if scores else 100.0

        return {
            "total_flags": total_flags,
            "flags_by_rule": flags_by_rule,
            "flags_by_severity": flags_by_severity,
            "flags_by_status": flags_by_status,
            "average_health_score": avg_score,
            "score_distribution": score_dist,
        }

    @classmethod
    async def get_trends(
        cls,
        db: AsyncSession,
        viewer_id: Optional[uuid.UUID] = None,
        viewer_role: Optional[str] = None,
        interval: str = "month",
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        # Fetch recent cycles
        c_query = select(ReviewCycle).order_by(ReviewCycle.created_at.desc()).limit(100)
        c_query = cls._apply_cycle_scope(c_query, viewer_id, viewer_role)
        cycles = (await db.execute(c_query)).scalars().all()

        # Build chronological buckets by YYYY-MM
        periods: Dict[str, Dict[str, int]] = {}

        for c in cycles:
            label = c.created_at.strftime("%Y-%m") if c.created_at else "2026-01"
            if label not in periods:
                periods[label] = {
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            periods[label]["cycles_created"] += 1

        # Fill evidence counts
        e_query = select(Evidence.created_at).join(ReviewCycle, Evidence.cycle_id == ReviewCycle.id)
        e_query = cls._apply_cycle_scope(e_query, viewer_id, viewer_role)
        e_res = (await db.execute(e_query)).scalars().all()
        for dt in e_res:
            label = dt.strftime("%Y-%m") if dt else "2026-01"
            if label not in periods:
                periods[label] = {
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            periods[label]["evidence_uploaded"] += 1

        # Fill feedback counts
        f_query = select(Feedback.created_at).join(ReviewCycle, Feedback.cycle_id == ReviewCycle.id)
        f_query = cls._apply_cycle_scope(f_query, viewer_id, viewer_role)
        f_res = (await db.execute(f_query)).scalars().all()
        for dt in f_res:
            label = dt.strftime("%Y-%m") if dt else "2026-01"
            if label not in periods:
                periods[label] = {
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            periods[label]["feedback_submitted"] += 1

        # Fill approved reports
        app_query = (
            select(Approval.created_at)
            .join(ReviewReport, Approval.report_id == ReviewReport.id)
            .join(ReviewCycle, ReviewReport.cycle_id == ReviewCycle.id)
            .where(Approval.decision == "approved")
        )
        app_query = cls._apply_cycle_scope(app_query, viewer_id, viewer_role)
        app_res = (await db.execute(app_query)).scalars().all()
        for dt in app_res:
            label = dt.strftime("%Y-%m") if dt else "2026-01"
            if label not in periods:
                periods[label] = {
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            periods[label]["reports_approved"] += 1

        # Fill bias flags
        b_query = select(BiasFlag.created_at).join(ReviewCycle, BiasFlag.cycle_id == ReviewCycle.id)
        b_query = cls._apply_cycle_scope(b_query, viewer_id, viewer_role)
        b_res = (await db.execute(b_query)).scalars().all()
        for dt in b_res:
            label = dt.strftime("%Y-%m") if dt else "2026-01"
            if label not in periods:
                periods[label] = {
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            periods[label]["bias_flags_raised"] += 1

        # Sort chronological
        sorted_labels = sorted(periods.keys())[-limit:]
        trend_points = [
            {
                "period_label": lbl,
                "cycles_created": periods[lbl]["cycles_created"],
                "reports_approved": periods[lbl]["reports_approved"],
                "evidence_uploaded": periods[lbl]["evidence_uploaded"],
                "feedback_submitted": periods[lbl]["feedback_submitted"],
                "bias_flags_raised": periods[lbl]["bias_flags_raised"],
            }
            for lbl in sorted_labels
        ]

        if not trend_points:
            # Baseline empty point if no data
            trend_points = [
                {
                    "period_label": date.today().strftime("%Y-%m"),
                    "cycles_created": 0,
                    "reports_approved": 0,
                    "evidence_uploaded": 0,
                    "feedback_submitted": 0,
                    "bias_flags_raised": 0,
                }
            ]

        return trend_points

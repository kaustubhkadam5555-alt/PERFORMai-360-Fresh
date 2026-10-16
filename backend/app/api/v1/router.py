from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    bias_audit,
    evidence,
    feedback,
    goals,
    health,
    reports,
    review_analysis,
    review_cycles,
    teams,
    users,
    workflows,
)

api_v1_router = APIRouter()

# Mount health endpoints
api_v1_router.include_router(health.router)

# Mount core foundational entity endpoints
api_v1_router.include_router(users.router)
api_v1_router.include_router(teams.router)
api_v1_router.include_router(review_cycles.router)

# Mount review workflow endpoints (Phase 3)
api_v1_router.include_router(feedback.router)
api_v1_router.include_router(goals.router)
api_v1_router.include_router(evidence.router)

# Mount AI review analysis endpoints (Phase 5)
api_v1_router.include_router(review_analysis.router)

# Mount Bias & Evidence-Quality Audit endpoints (Phase 6)
api_v1_router.include_router(bias_audit.router)

# Mount LangGraph Multi-Agent Orchestration endpoints (Phase 7)
api_v1_router.include_router(workflows.router)

# Mount Human Approval, Report Versioning & Governance endpoints (Phase 8)
api_v1_router.include_router(reports.router)

# Mount Analytics & Trends endpoints (Phase 9)
api_v1_router.include_router(analytics.router)

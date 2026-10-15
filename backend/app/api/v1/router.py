from fastapi import APIRouter

from app.api.v1.endpoints import (
    evidence,
    feedback,
    goals,
    health,
    review_analysis,
    review_cycles,
    teams,
    users,
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

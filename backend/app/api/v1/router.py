from fastapi import APIRouter

from app.api.v1.endpoints import health, review_cycles, teams, users

api_v1_router = APIRouter()

# Mount health endpoints
api_v1_router.include_router(health.router)

# Mount core foundational entity endpoints
api_v1_router.include_router(users.router)
api_v1_router.include_router(teams.router)
api_v1_router.include_router(review_cycles.router)

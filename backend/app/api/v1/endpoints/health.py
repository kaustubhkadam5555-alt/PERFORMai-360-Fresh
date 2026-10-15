from typing import Any, Dict

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    dependencies: Dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Confirms that the FastAPI process is active and accepting requests.",
)
async def liveness_probe() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "All dependencies are healthy and ready to accept traffic."},
        503: {"description": "One or more dependencies (e.g. database) are unavailable."},
    },
    summary="Readiness Probe",
    description="Checks whether core dependencies including PostgreSQL are connected and ready.",
)
async def readiness_probe(response: Response) -> ReadinessResponse:
    db_connected, db_message = await check_database_connection()

    dependencies = {
        "database": {
            "status": "ready" if db_connected else "unhealthy",
            "message": db_message,
        },
        "llm_provider": {
            "status": "ready",
            "provider": settings.LLM_PROVIDER,
            "mode": "offline/mock" if settings.LLM_PROVIDER == "mock" else "active",
        },
    }

    if not db_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unready"
    else:
        response.status_code = status.HTTP_200_OK
        overall_status = "ready"

    return ReadinessResponse(
        status=overall_status,
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        dependencies=dependencies,
    )

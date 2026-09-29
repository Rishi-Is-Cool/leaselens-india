from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db import check_database

router = APIRouter(tags=["health"])


class DatabaseHealth(BaseModel):
    connected: bool
    server_version: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    demo_mode: bool
    retention_hours: int
    database: DatabaseHealth


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    db = check_database()
    return HealthResponse(
        # 200 either way: the API is live. `status` distinguishes a healthy
        # process from one that cannot reach Postgres, so the UI can say which.
        status="ok" if db.connected else "degraded",
        service=settings.app_name,
        environment=settings.environment,
        demo_mode=settings.demo_mode,
        retention_hours=settings.retention_hours,
        database=DatabaseHealth(
            connected=db.connected,
            server_version=db.server_version,
            error=db.error,
        ),
    )

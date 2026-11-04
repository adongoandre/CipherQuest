"""Health check endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.mission import HealthResponse

router = APIRouter(tags=["system"])

VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse, summary="Liveness and database check")
def health(response: Response, db: DbSession = Depends(get_db)) -> HealthResponse:
    """Returns 200 when the API is up and the database answers a query."""
    settings = get_settings()

    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # pragma: no cover - exercised only on a broken DB
        database = "error"
        response.status_code = 503

    kind = "sqlite" if settings.is_sqlite else "postgresql"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        app_env=settings.app_env,
        database=f"{kind}:{database}",
        version=VERSION,
        time=datetime.now(timezone.utc),
    )

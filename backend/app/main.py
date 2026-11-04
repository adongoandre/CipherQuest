"""CipherQuest FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging import configure_logging
from app.seed import ensure_demo_players, ensure_seeded

logger = logging.getLogger(__name__)

API_DESCRIPTION = """
CipherQuest is an educational encryption game. Players solve a riddle to
discover a cipher parameter, read a separate contextual clue, decrypt a
message, and receive a worked explanation.

Classical ciphers taught here are **educational demonstrations only** and are
not suitable for protecting real confidential information.
""".strip()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Bootstrap tables and seed content when the database is empty."""
    settings = get_settings()
    configure_logging(settings.log_level)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if ensure_seeded(db):
            logger.info("seeded mission content into an empty database")
        ensure_demo_players(db)
    finally:
        db.close()

    logger.info(
        "cipherquest api started",
        extra={"app_env": settings.app_env, "database": settings.database_url.split("://")[0]},
    )
    yield
    engine.dispose()


def create_app() -> FastAPI:
    """Build the application instance."""
    settings = get_settings()

    app = FastAPI(
        title="CipherQuest API",
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Session-Token"],
        expose_headers=["X-Session-Token"],
    )

    @app.middleware("http")
    async def attach_session_header(request: Request, call_next):
        """Hand the resolved guest token back to the caller on every response."""
        response = await call_next(request)
        token = getattr(request.state, "session_token", None)
        if token:
            response.headers["X-Session-Token"] = token
        return response

    install_error_handlers(app)
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "CipherQuest API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
            "note": "Classical ciphers are for education, not real-world security.",
        }

    return app


app = create_app()

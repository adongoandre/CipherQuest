"""Version 1 API router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    academy,
    admin,
    auth,
    compete,
    engagement,
    health,
    home,
    missions,
    profile,
    progress,
    rooms,
    sessions,
    social,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(sessions.router)
api_router.include_router(missions.router)
api_router.include_router(progress.router)
api_router.include_router(engagement.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(home.router)
api_router.include_router(compete.router)
api_router.include_router(social.router)
api_router.include_router(academy.router)
api_router.include_router(rooms.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]

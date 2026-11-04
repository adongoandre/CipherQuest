"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.models import PlayerSession
from app.services.missions import resolve_session

SESSION_HEADER = "X-Session-Token"


def get_session(
    request: Request,
    db: DbSession = Depends(get_db),
) -> PlayerSession:
    """Resolve the caller's pseudonymous session, creating one if needed.

    The resolved token is published on ``request.state.session_token`` so the
    response middleware can hand it back to the client exactly once.
    """
    token = request.headers.get(SESSION_HEADER)
    session, created = resolve_session(db, token)
    request.state.session_token = session.token
    request.state.session_created = created
    return session


__all__ = ["SESSION_HEADER", "get_db", "get_session"]

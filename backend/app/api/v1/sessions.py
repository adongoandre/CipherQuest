"""Guest session creation.

The MVP uses a lightweight pseudonymous session instead of accounts. The
client calls this once, stores the returned token, and sends it back as
``X-Session-Token`` on every later request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_session
from app.core.database import get_db
from app.models import PlayerSession
from app.schemas.engagement import SessionResponse

router = APIRouter(prefix="/session", tags=["session"])


@router.post("", response_model=SessionResponse, summary="Create or resume a guest session")
def create_session(
    request: Request,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> SessionResponse:
    created = bool(getattr(request.state, "session_created", False))
    db.commit()
    return SessionResponse(
        token=session.token,
        display_name=session.display_name,
        created=created,
    )

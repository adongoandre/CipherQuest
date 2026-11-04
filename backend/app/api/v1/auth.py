"""Auth endpoints: register (upgrade guest), login, current identity."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.models import PlayerSession
from app.schemas.account import LoginRequest, ProfileResponse, RegisterRequest
from app.schemas.engagement import SessionResponse
from app.services.accounts import authenticate, register_account
from app.services.profile import build_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SessionResponse)
def register(
    payload: RegisterRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> SessionResponse:
    """Create an account on the current guest session, keeping all progress."""
    register_account(
        db,
        session,
        display_name=payload.display_name,
        email=payload.email,
        password=payload.password,
        accepted_terms=payload.accepted_terms,
    )
    return SessionResponse(token=session.token, display_name=session.display_name, created=False)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, db: DbSession = Depends(get_db)) -> SessionResponse:
    """Verify credentials and hand back the account session's token."""
    account = authenticate(db, email=payload.email, password=payload.password)
    return SessionResponse(token=account.token, display_name=account.display_name, created=False)


@router.get("/me", response_model=ProfileResponse)
def me(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ProfileResponse:
    return build_profile(db, session)


__all__ = ["router"]
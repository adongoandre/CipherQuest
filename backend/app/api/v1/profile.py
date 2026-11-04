"""Profile and settings endpoints (Profile + Settings screens)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.models import PlayerSession
from app.schemas.account import ProfileResponse, SettingsResponse, SettingsUpdateRequest
from app.services.accounts import unique_display_name
from app.services.profile import build_profile, merge_preferences, preferences_of

router = APIRouter(tags=["profile"])


def _settings(session: PlayerSession) -> SettingsResponse:
    prefs = preferences_of(session)
    return SettingsResponse(
        display_name=session.display_name,
        email=session.email,
        is_guest=session.password_hash is None,
        accessibility=prefs["accessibility"],
        privacy=prefs["privacy"],
        play_style=prefs["play_style"],
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ProfileResponse:
    return build_profile(db, session)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    _db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> SettingsResponse:
    return _settings(session)


@router.post("/settings", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> SettingsResponse:
    if payload.display_name is not None:
        unique_display_name(db, payload.display_name, exclude_id=session.id)
        session.display_name = payload.display_name
    merge_preferences(
        session,
        accessibility=payload.accessibility,
        privacy=payload.privacy,
        play_style=payload.play_style,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _settings(session)


@router.post("/account/delete")
def delete_account(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> dict:
    """Delete the signed-in player's account and every row that belongs to it.

    Child rows (attempts, lessons, friendships, cup entries) cascade from
    ``player_sessions.id``; audit references are nulled by their FK.
    """
    db.delete(session)
    db.commit()
    return {"deleted": True, "message": "Account and progress deleted."}


__all__ = ["router"]
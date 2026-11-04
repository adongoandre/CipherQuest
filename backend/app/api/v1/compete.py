"""Compete endpoints: leaderboards and the Weekly Free Cup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.models import PlayerSession
from app.schemas.compete import (
    CupState,
    EnterCupResponse,
    LeaderboardResponse,
    LeaderboardScope,
)
from app.services.compete import build_cup, build_leaderboard, enter_cup

router = APIRouter(prefix="/compete", tags=["compete"])


@router.get("/leaderboards", response_model=LeaderboardResponse)
def leaderboards(
    scope: LeaderboardScope = Query(default="week"),
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> LeaderboardResponse:
    return build_leaderboard(db, session, scope)


@router.get("/cup", response_model=CupState)
def cup(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> CupState:
    return build_cup(db, session)


@router.post("/cup/enter", response_model=EnterCupResponse)
def enter(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> EnterCupResponse:
    entered, week, message = enter_cup(db, session)
    return EnterCupResponse(entered=entered, week=week, message=message)


__all__ = ["router"]
"""Room endpoints: create, join, poll, ready, leave, start."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.models import PlayerSession, RoomMode
from app.schemas.room import CreateRoomRequest, JoinRoomRequest, ReadyRequest, RoomState
from app.services import rooms as room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomState)
def create(
    payload: CreateRoomRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    mode = RoomMode.TEAM_ESCAPE if payload.mode == "team_escape" else RoomMode.DUEL
    room = room_service.create_room(db, session, mode)
    return room_service.build_state(db, room, session)


@router.post("/join", response_model=RoomState)
def join(
    payload: JoinRoomRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    room = room_service.join_room(db, payload.code, session)
    return room_service.build_state(db, room, session)


@router.get("/{code}", response_model=RoomState)
def state(
    code: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    room = room_service.resolve_room(db, code)
    return room_service.build_state(db, room, session)


@router.post("/{code}/ready", response_model=RoomState)
def ready(
    code: str,
    payload: ReadyRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    room = room_service.set_ready(db, code, session, payload.ready)
    return room_service.build_state(db, room, session)


@router.post("/{code}/leave", response_model=RoomState)
def leave(
    code: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    room = room_service.leave_room(db, code, session)
    return room_service.build_state(db, room, session)


@router.post("/{code}/start", response_model=RoomState)
def start(
    code: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RoomState:
    room = room_service.start_game(db, code, session)
    return room_service.build_state(db, room, session)


__all__ = ["router"]
"""Room creation, joining, readiness and start (Team Escape / Cipher Duel)."""

from __future__ import annotations

import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models import (
    Mission,
    PlayerSession,
    PublicationStatus,
    Room,
    RoomMode,
    RoomPlayer,
    RoomStatus,
)
from app.schemas.room import RoomPlayerEntry, RoomState

# Unambiguous alphabet: no 0/O or 1/I confusion when a code is read aloud.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 3
MAX_TEAM = 4
MAX_DUEL = 2


def generate_code(db: DbSession) -> str:
    for _ in range(50):
        letters = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH * 2))
        code = f"{letters[:CODE_LENGTH]}-{letters[CODE_LENGTH:]}"
        exists = db.scalar(select(Room.id).where(Room.code == code))
        if exists is None:
            return code
    raise HTTPException(  # pragma: no cover
        status_code=500,
        detail={"code": "room_code_exhausted", "message": "Could not allocate a room code."},
    )


def max_players(mode: RoomMode) -> int:
    return MAX_DUEL if mode == RoomMode.DUEL else MAX_TEAM


def create_room(db: DbSession, host: PlayerSession, mode: RoomMode) -> Room:
    """Create (or reuse) the host's open room and seat them."""
    existing = db.scalar(
        select(Room).where(
            Room.host_session_id == host.id, Room.status == RoomStatus.WAITING
        )
    )
    if existing is not None:
        room = existing
        room.mode = mode
    else:
        room = Room(code=generate_code(db), host_session_id=host.id, mode=mode)
        db.add(room)
        db.flush()
    _add_player(db, room, host)
    db.commit()
    db.refresh(room)
    return room


def _add_player(db: DbSession, room: Room, player: PlayerSession) -> RoomPlayer:
    row = db.scalar(
        select(RoomPlayer).where(
            RoomPlayer.room_id == room.id, RoomPlayer.session_id == player.id
        )
    )
    if row is None:
        row = RoomPlayer(room_id=room.id, session_id=player.id)
        db.add(row)
        db.flush()
    return row


def resolve_room(db: DbSession, code: str) -> Room:
    room = db.scalar(select(Room).where(Room.code == code.upper()))
    if room is None or room.status == RoomStatus.ABANDONED:
        raise HTTPException(
            status_code=404,
            detail={"code": "room_not_found", "message": "That room code does not exist."},
        )
    return room


def join_room(db: DbSession, code: str, player: PlayerSession) -> Room:
    room = resolve_room(db, code)
    if room.status != RoomStatus.WAITING:
        raise HTTPException(
            status_code=409,
            detail={"code": "room_started", "message": "That game has already started."},
        )
    members = _players(db, room)
    if player.id not in [m.id for m in members] and len(members) >= max_players(room.mode):
        raise HTTPException(
            status_code=409, detail={"code": "room_full", "message": "That room is full."}
        )
    _add_player(db, room, player)
    db.commit()
    db.refresh(room)
    return room


def _players(db: DbSession, room: Room) -> list[PlayerSession]:
    rows = db.execute(
        select(PlayerSession)
        .join(RoomPlayer, RoomPlayer.session_id == PlayerSession.id)
        .where(RoomPlayer.room_id == room.id)
        .order_by(RoomPlayer.joined_at)
    ).scalars()
    return list(rows)


def _ready_map(db: DbSession, room: Room) -> dict[int, bool]:
    rows = db.execute(
        select(RoomPlayer.session_id, RoomPlayer.ready).where(RoomPlayer.room_id == room.id)
    ).all()
    return {int(sid): bool(ready) for sid, ready in rows}


def build_state(db: DbSession, room: Room, viewer: PlayerSession) -> RoomState:
    members = _players(db, room)
    ready = _ready_map(db, room)
    entries = [
        RoomPlayerEntry(
            session_id=m.id,
            display_name=m.display_name or "Guest",
            ready=bool(ready.get(m.id, False)),
            is_host=m.id == room.host_session_id,
        )
        for m in members
    ]
    mission_slug = mission_title = None
    if room.mission_id:
        mission = db.get(Mission, room.mission_id)
        if mission is not None:
            mission_slug, mission_title = mission.slug, mission.title
    return RoomState(
        code=room.code,
        mode=room.mode.value,
        status=room.status.value,
        host_session_id=room.host_session_id,
        players=entries,
        max_players=max_players(room.mode),
        you_are_host=viewer.id == room.host_session_id,
        you_are_ready=bool(ready.get(viewer.id, False)),
        everyone_ready=bool(entries) and all(e.ready for e in entries),
        mission_slug=mission_slug,
        mission_title=mission_title,
    )


def set_ready(db: DbSession, code: str, player: PlayerSession, ready: bool) -> Room:
    room = resolve_room(db, code)
    row = db.scalar(
        select(RoomPlayer).where(
            RoomPlayer.room_id == room.id, RoomPlayer.session_id == player.id
        )
    )
    if row is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "not_in_room", "message": "Join the room first."},
        )
    row.ready = ready
    db.commit()
    return room


def leave_room(db: DbSession, code: str, player: PlayerSession) -> Room:
    room = resolve_room(db, code)
    row = db.scalar(
        select(RoomPlayer).where(
            RoomPlayer.room_id == room.id, RoomPlayer.session_id == player.id
        )
    )
    if row is None:
        raise HTTPException(
            status_code=403,
            detail={"code": "not_in_room", "message": "You are not in that room."},
        )
    db.delete(row)
    if room.host_session_id == player.id:
        remaining = _players(db, room)
        if remaining:
            room.host_session_id = remaining[0].id
        else:
            room.status = RoomStatus.ABANDONED
    db.commit()
    db.refresh(room)
    return room


def start_game(
    db: DbSession, code: str, host: PlayerSession, mission_slug: str | None = None
) -> Room:
    from datetime import datetime, timezone

    room = resolve_room(db, code)
    if room.host_session_id != host.id:
        raise HTTPException(
            status_code=403,
            detail={"code": "not_host", "message": "Only the host can start the game."},
        )
    members = _players(db, room)
    ready = _ready_map(db, room)
    if len(members) < 2:
        raise HTTPException(
            status_code=409,
            detail={"code": "players_missing", "message": "Waiting for at least one more player."},
        )
    if not all(ready.get(m.id, False) for m in members):
        raise HTTPException(
            status_code=409,
            detail={"code": "players_not_ready", "message": "Every player must be ready."},
        )
    mission = None
    if mission_slug:
        mission = db.scalar(
            select(Mission).where(
                Mission.slug == mission_slug,
                Mission.status == PublicationStatus.PUBLISHED,
            )
        )
    if mission is None:
        mission = db.scalar(
            select(Mission)
            .where(Mission.status == PublicationStatus.PUBLISHED)
            .order_by(Mission.id)
        )
    if mission is None:  # pragma: no cover - seed guarantees published missions
        raise HTTPException(
            status_code=409,
            detail={"code": "no_mission", "message": "No published mission is available."},
        )
    room.mission_id = mission.id
    room.status = RoomStatus.IN_PROGRESS
    room.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return room


__all__ = [
    "build_state",
    "create_room",
    "generate_code",
    "join_room",
    "leave_room",
    "max_players",
    "resolve_room",
    "set_ready",
    "start_game",
]
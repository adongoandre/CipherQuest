"""Multiplayer rooms for Team Escape and Cipher Duel.

Rooms are short-lived: a code, a host, up to four players and a ready state.
Once every player is ready the host starts the game and the room moves to
``in_progress``; finished/abandoned rooms are never reused.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RoomStatus(str, enum.Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class RoomMode(str, enum.Enum):
    TEAM_ESCAPE = "team_escape"
    DUEL = "duel"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(8), unique=True, nullable=False, index=True
    )
    host_session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mode: Mapped[RoomMode] = mapped_column(
        Enum(RoomMode, name="room_mode"), nullable=False, default=RoomMode.TEAM_ESCAPE
    )
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="room_status"), nullable=False, default=RoomStatus.WAITING
    )
    # The published mission this room will play once started (chosen by the host).
    mission_id: Mapped[int | None] = mapped_column(
        ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RoomPlayer(Base):
    __tablename__ = "room_players"
    __table_args__ = (UniqueConstraint("room_id", "session_id", name="uq_room_player"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ready: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

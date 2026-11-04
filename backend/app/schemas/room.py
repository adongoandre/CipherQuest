"""Multiplayer room schemas (Team Escape lobby, Cipher Duel)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoomPlayerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int
    display_name: str
    ready: bool
    is_host: bool


class RoomState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    mode: Literal["team_escape", "duel"]
    status: Literal["waiting", "in_progress", "finished", "abandoned"]
    host_session_id: int
    players: list[RoomPlayerEntry]
    max_players: int
    you_are_host: bool
    you_are_ready: bool
    everyone_ready: bool
    mission_slug: str | None = None
    mission_title: str | None = None


class CreateRoomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["team_escape", "duel"] = "team_escape"


class JoinRoomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=7, max_length=8, pattern=r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")


class ReadyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool
"""Leaderboards and Weekly Free Cup schemas (Compete screens)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LeaderboardScope = Literal["week", "friends", "season", "all_time"]


class StandingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    display_name: str
    score: int
    missions: int
    change: int | None = None  # places gained/lost vs previous period, if known
    is_you: bool = False


class YourPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    score: int
    missions: int
    gap_to_next: int  # XP needed to overtake the rank above (0 when rank 1)
    next_rank_name: str | None = None


class LeaderboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: LeaderboardScope
    standings: list[StandingEntry]
    you: YourPosition | None
    footer: str
    total_players: int


class CupState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week: str  # ISO week key, e.g. 2026-W44
    label: str  # e.g. "Saturday 10:00 – Sunday 20:00 (UTC)"
    status: Literal["scheduled", "open", "closed"]
    opens_at: datetime
    closes_at: datetime
    seconds_until_open: int
    seconds_until_close: int
    participants: int
    you_entered: bool
    your_score: int
    standings: list[StandingEntry]
    you: YourPosition | None
    note: str


class EnterCupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entered: bool
    week: str
    message: str
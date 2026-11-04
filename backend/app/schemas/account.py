"""Auth, profile and settings schemas (Join, Profile, Settings screens)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AccessibilityToggle = Literal[
    "high_contrast_text",
    "reduce_motion",
    "dyslexic_friendly_font",
    "larger_text",
    "sound_effects",
]
PrivacyToggle = Literal["show_display_name", "anonymous_leaderboards", "share_anonymous_data"]
PlayStyleToggle = Literal["timed_challenges", "daily_reminder"]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_ .-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    accepted_terms: bool = Field(default=False)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Badge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    description: str
    earned: bool


class CipherMastery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cipher: str
    name: str
    lessons_completed: int
    lessons_total: int


class RecentMission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    best_score: int | None = None
    completed_at: datetime | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    is_guest: bool
    is_admin: bool
    level: int
    xp: int
    level_ceiling: int
    level_floor: int
    missions_solved: int
    streak_days: int
    longest_streak: int
    accuracy: int
    hints_used: int
    average_score: int
    time_played_minutes: int
    badges: list[Badge]
    mastery: list[CipherMastery]
    recent_missions: list[RecentMission]
    joined_at: datetime


class SettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    email: str | None = None
    is_guest: bool
    accessibility: dict[str, bool]
    privacy: dict[str, bool]
    play_style: dict[str, bool]


class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=3, max_length=24)
    accessibility: dict[str, bool] | None = None
    privacy: dict[str, bool] | None = None
    play_style: dict[str, bool] | None = None
"""Session and feedback schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mission import ProgressSummary

LearnedChoice = Literal["yes", "a_little", "no"]
WouldReturnChoice = Literal["yes", "maybe", "no"]


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    display_name: str | None = None
    created: bool


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_slug: str = Field(min_length=1, max_length=80)
    clarity_rating: int | None = Field(default=None, ge=1, le=5)
    learned: LearnedChoice | None = None
    enjoyment_rating: int | None = Field(default=None, ge=1, le=5)
    would_return: WouldReturnChoice | None = None
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    saved: bool
    message: str


class ProgressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    progress: ProgressSummary
    missions: list[dict]

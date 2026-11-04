"""Academy schemas: tracks, lesson lists and lesson pages."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LessonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    title: str
    summary: str
    completed: bool


class TrackSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    blurb: str
    difficulty: str
    lessons_total: int
    lessons_completed: int
    current_step: int
    status: Literal["not_started", "in_progress", "complete"]


class AcademyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tracks: list[TrackSummary]
    total_lessons_completed: int
    total_lessons: int
    suggested_next: Literal["caesar", "atbash", "vigenere", "rail-fence", "playfair", "columnar", "baconian", "substitution"] | None


class TrackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    blurb: str
    difficulty: str
    lessons: list[LessonSummary]
    current_step: int
    xp_available: int


class LessonExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str | None = None
    output: str | None = None
    caption: str | None = None
    interactive: str | None = None
    sample_text: str | None = None
    default_shift: int | None = None


class LessonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    track_name: str
    step: int
    title: str
    summary: str
    body: list[str]
    example: LessonExample | None = None
    completed: bool
    xp_awarded: int
    next_step: int | None
    total_steps: int


class LessonCompleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed: bool
    xp_awarded: int
    total_xp: int
    lessons_completed: int
    next_step: int | None
    finished_track: bool
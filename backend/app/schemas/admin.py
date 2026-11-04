"""Admin mission-editor schemas (author, verify, publish, audit)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AdminMissionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    title: str
    status: Literal["draft", "published", "retired"]
    difficulty: str
    cipher_type: str
    updated_at: datetime | None = None
    verified: bool = False
    verify_problems: list[str] = Field(default_factory=list)


class MissionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    narrative: str = Field(min_length=20, max_length=4000)
    riddle_prompt: str = Field(min_length=10, max_length=1500)
    accepted_riddle_answers: list[str] = Field(min_length=1, max_length=6)
    key_rule_description: str = Field(default="The number of letters in the riddle answer")
    contextual_clue: str = Field(min_length=10, max_length=1500)
    plaintext_answer: str = Field(min_length=5, max_length=300)
    hints: list[str] = Field(default_factory=list, max_length=3)
    difficulty: Literal["beginner", "intermediate", "advanced", "expert"] = "beginner"
    cipher_type: Literal["caesar"] = "caesar"
    estimated_minutes: int = Field(default=5, ge=1, le=60)


class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool
    problems: list[str]
    round_trip_ok: bool
    parameter: int | None = None
    ciphertext: str | None = None
    plaintext: str | None = None


class AdminMissionDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    title: str
    status: Literal["draft", "published", "retired"]
    difficulty: str
    cipher_type: str
    estimated_minutes: int
    narrative: str
    riddle_prompt: str
    accepted_riddle_answers: list[str]
    key_rule_description: str
    contextual_clue: str
    plaintext_answer: str
    hints: list[str]
    parameter: int | None = None
    ciphertext: str | None = None
    verification: VerifyResult
    updated_at: datetime | None = None


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    status: Literal["draft", "published", "retired"]
    message: str


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    action: str
    entity_type: str
    entity_id: str
    detail: dict[str, Any]
    created_at: datetime


class AuditListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[AuditEntry]
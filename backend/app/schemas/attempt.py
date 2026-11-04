"""Request/response schemas for the mission loop."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mission import KeyReveal, MissionStage, ScoreBreakdown, Solution


class RiddleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=120)
    idempotency_key: str | None = Field(default=None, max_length=64)


class RiddleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: bool
    stage: MissionStage
    attempts: int
    key_reveal: KeyReveal | None = None
    message: str


class ContextClueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: MissionStage
    contextual_clue: str
    ciphertext: str


class HintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hint_number: int
    total_hints: int
    hint: str
    hints_used: int
    score_penalty_note: str


class DecryptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=500)
    elapsed_seconds: int | None = Field(default=None, ge=0, le=86_400)
    idempotency_key: str | None = Field(default=None, max_length=64)


class DecryptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: bool
    stage: MissionStage
    attempts: int
    hints_used: int
    score: ScoreBreakdown | None = None
    solution: Solution | None = None
    message: str
    progress_awarded: bool = False
    # Teaching content revealed together with the solution; never sent earlier.
    comprehension_check: dict[str, Any] | None = None


class RevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Literal["stuck", "finished"] = "stuck"


class RevealResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: MissionStage
    solution: Solution
    score_awarded: int = 0
    message: str


class ComprehensionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: int = Field(ge=0, le=5)
    idempotency_key: str | None = Field(default=None, max_length=64)


class ComprehensionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: bool
    earned: int
    total: int
    correct_index: int
    explanation: str
    awarded: bool

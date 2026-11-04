"""Stage-gated public mission payloads.

The single most important rule encoded here: a mission response contains only
the fields the current stage needs. ``plaintext_answer``,
``accepted_riddle_answers``, the ciphertext and the scoring configuration are
absent until the stage that is entitled to reveal them.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MissionStage(str, enum.Enum):
    """Server-authoritative progress through one mission for one session."""

    RIDDLE = "riddle"
    KEY_REVEAL = "key_reveal"
    CONTEXT_CLUE = "context_clue"
    DECRYPT = "decrypt"
    EXPLANATION = "explanation"


class KeyReveal(BaseModel):
    """Revealed only after a correct riddle answer.

    Carries the worked-out key (rule + numeric shift): the mockups show both on
    the "key revealed" and decryption panels once the riddle is solved. Nothing
    is exposed before that — the field is absent while the riddle is open.
    """

    model_config = ConfigDict(extra="forbid")

    accepted_answer: str
    key_type: str
    parameter: int
    key_rule_description: str


class MissionBrief(BaseModel):
    """Always safe to send."""

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    title: str
    narrative: str
    difficulty: str
    cipher_type: str
    cipher_name: str
    estimated_minutes: int
    stage: MissionStage
    hint_count_total: int
    hints_revealed: int
    is_completed: bool
    # Which telling of the mission this session is playing (1-based) and how
    # many tellings exist in total — replays of a solved mission serve the
    # next one.
    telling_number: int
    telling_count: int


class MissionRiddle(MissionBrief):
    riddle_prompt: str


class MissionKeyReveal(MissionBrief):
    key_reveal: KeyReveal


class MissionContextClue(MissionBrief):
    key_reveal: KeyReveal
    contextual_clue: str


class MissionDecrypt(MissionBrief):
    key_reveal: KeyReveal
    contextual_clue: str
    ciphertext: str
    # Hints this session already earned. Only *undelivered* hints stay hidden.
    revealed_hints: list[str] = Field(default_factory=list)


class Solution(BaseModel):
    """Only present once the stage reaches EXPLANATION."""

    plaintext: str
    explanation: str
    worked_example: str


class MissionExplanation(MissionDecrypt):
    solution: Solution
    # Teaching content, safe to expose only once the solution itself is revealed.
    comprehension_check: dict[str, Any] | None = None
    # Score this session actually earned, so a reload still shows the real
    # result instead of looking like an unrevealed solution.
    earned_score: ScoreBreakdown | None = None
    comprehension_awarded: bool = False


class MissionListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    title: str
    difficulty: str
    cipher_type: str
    estimated_minutes: int
    display_order: int
    is_completed: bool


class MissionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missions: list[MissionListItem]
    daily_slug: str


class ProgressSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missions_completed: int
    total_puzzles_solved: int
    total_score: int
    xp: int
    completed_slugs: list[str]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    app_env: str
    database: str
    version: str
    time: datetime


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    solve_points: int
    no_hint_bonus: int
    time_bonus: int
    comprehension_bonus: int
    hints_used: int
    elapsed_seconds: int | None = None
    breakdown: dict[str, Any]

"""Server-authoritative scoring.

Rules (MVP Master Prompt §8):

* Correct final decryption: up to 70 points.
* Optional time bonus: 0–15 points, only for timed missions, never dominant.
* No-hint bonus: 10 points.
* Comprehension/explanation check: 5 points.

The client never supplies a score. Every value here is computed from
server-side state and returned to the client purely for display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SOLVE_POINTS = 70
NO_HINT_BONUS = 10
COMPREHENSION_BONUS = 5
TIME_BONUS_MAX = 15
MAX_TOTAL = 100


@dataclass(frozen=True, slots=True)
class ScoreResult:
    total: int
    solve_points: int
    no_hint_bonus: int
    time_bonus: int
    comprehension_bonus: int
    hints_used: int
    elapsed_seconds: int | None
    breakdown: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "solve_points": self.solve_points,
            "no_hint_bonus": self.no_hint_bonus,
            "time_bonus": self.time_bonus,
            "comprehension_bonus": self.comprehension_bonus,
            "hints_used": self.hints_used,
            "elapsed_seconds": self.elapsed_seconds,
            "breakdown": self.breakdown,
        }


def time_bonus(elapsed_seconds: int | None, target_seconds: int) -> int:
    """0–15 points, decaying linearly to zero at the mission's target duration.

    Returns 0 when timing is disabled (``target_seconds <= 0``) or no elapsed
    time was supplied, so untimed practice is never penalised.
    """
    if target_seconds <= 0 or elapsed_seconds is None or elapsed_seconds < 0:
        return 0
    if elapsed_seconds >= target_seconds:
        return 0
    return int(round(TIME_BONUS_MAX * (1 - elapsed_seconds / target_seconds)))


def compute_score(
    *,
    correct: bool,
    hints_used: int,
    elapsed_seconds: int | None,
    timed: bool,
    target_seconds: int,
) -> ScoreResult:
    """Compute the score for a completed decrypt submission."""
    if not correct:
        return ScoreResult(
            total=0,
            solve_points=0,
            no_hint_bonus=0,
            time_bonus=0,
            comprehension_bonus=0,
            hints_used=hints_used,
            elapsed_seconds=elapsed_seconds,
            breakdown={
                "correct": False,
                "note": "Incorrect answers earn no solve points.",
            },
        )

    solve = SOLVE_POINTS
    no_hint = NO_HINT_BONUS if hints_used == 0 else 0
    bonus = time_bonus(elapsed_seconds, target_seconds) if timed else 0

    return ScoreResult(
        total=solve + no_hint + bonus,
        solve_points=solve,
        no_hint_bonus=no_hint,
        time_bonus=bonus,
        comprehension_bonus=0,
        hints_used=hints_used,
        elapsed_seconds=elapsed_seconds,
        breakdown={
            "correct": True,
            "solve_points": f"+{solve} correct decryption",
            "no_hint_bonus": f"+{no_hint} solved without hints" if no_hint else "+0 hints were used",
            "time_bonus": f"+{bonus} time bonus" if bonus else "+0 timing disabled or target reached",
        },
    )

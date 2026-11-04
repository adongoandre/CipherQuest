"""Unit tests for the server-authoritative scoring rules."""

from __future__ import annotations

import pytest

from app.services import analytics, scoring


def _score(**overrides):
    defaults = dict(
        correct=True,
        hints_used=0,
        elapsed_seconds=None,
        timed=False,
        target_seconds=300,
    )
    defaults.update(overrides)
    return scoring.compute_score(**defaults)


# --- base components -------------------------------------------------------


def test_correct_no_hints_untimed_scores_80() -> None:
    result = _score()
    assert result.solve_points == 70
    assert result.no_hint_bonus == 10
    assert result.time_bonus == 0
    assert result.total == 80


def test_incorrect_answer_scores_zero() -> None:
    result = _score(correct=False, hints_used=3)
    assert result.total == 0
    assert result.solve_points == 0
    assert result.no_hint_bonus == 0
    assert result.breakdown["correct"] is False


@pytest.mark.parametrize("hints", [1, 2, 3])
def test_any_hint_removes_the_no_hint_bonus(hints: int) -> None:
    result = _score(hints_used=hints)
    assert result.no_hint_bonus == 0
    assert result.total == 70
    assert "hints were used" in result.breakdown["no_hint_bonus"]


def test_no_hint_bonus_is_awarded_only_when_correct() -> None:
    result = _score(correct=False, hints_used=0)
    assert result.no_hint_bonus == 0


# --- time bonus boundaries -------------------------------------------------


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (0, 15),      # instant solve: full bonus
        (150, 8),     # halfway to target -> round(7.5) = 8
        (299, 0),     # within one second of target: only 0.05 points, rounds to 0
        (300, 0),     # exactly at target: no bonus
        (9999, 0),    # far beyond target: no bonus and no penalty
        (-5, 0),      # defensive: a negative clock never yields a bonus
    ],
)
def test_time_bonus_boundaries(elapsed: int, expected: int) -> None:
    assert scoring.time_bonus(elapsed, 300) == expected


def test_time_bonus_is_never_dominant() -> None:
    for elapsed in range(0, 600, 7):
        assert scoring.time_bonus(elapsed, 300) <= scoring.TIME_BONUS_MAX


def test_time_bonus_is_zero_when_timing_is_disabled() -> None:
    assert scoring.time_bonus(10, 0) == 0
    assert scoring.time_bonus(None, 300) == 0


def test_timed_solve_never_exceeds_the_configured_maximum() -> None:
    result = _score(timed=True, elapsed_seconds=0, target_seconds=300)
    assert result.time_bonus == 15
    assert result.total == 70 + 10 + 15
    assert result.total <= 100


def test_untimed_mode_ignores_elapsed_time() -> None:
    result = _score(timed=False, elapsed_seconds=1, target_seconds=300)
    assert result.time_bonus == 0
    assert result.total == 80


def test_elapsed_time_is_reported_for_display() -> None:
    result = _score(elapsed_seconds=42)
    assert result.elapsed_seconds == 42


def test_comprehension_bonus_keeps_total_within_100() -> None:
    best_case = (
        scoring.SOLVE_POINTS
        + scoring.TIME_BONUS_MAX
        + scoring.NO_HINT_BONUS
        + scoring.COMPREHENSION_BONUS
    )
    assert best_case == scoring.MAX_TOTAL == 100


def test_score_serialises_to_a_flat_dict() -> None:
    payload = _score().as_dict()
    assert set(payload) == {
        "total", "solve_points", "no_hint_bonus", "time_bonus",
        "comprehension_bonus", "hints_used", "elapsed_seconds", "breakdown",
    }


# --- analytics privacy guards ----------------------------------------------


def test_analytics_rejects_unknown_events() -> None:
    with pytest.raises(ValueError, match="unknown analytics event"):
        analytics.record(object(), "made_up_event")  # type: ignore[arg-type]


def test_analytics_rejects_raw_answers_and_personal_data() -> None:
    with pytest.raises(ValueError, match="must not carry raw answers"):
        analytics.record(object(), "hint_used", answer="secret")  # type: ignore[arg-type]


def test_analytics_allowlist_is_explicit() -> None:
    assert "landing_view" in analytics.allowed_events()
    assert "mission_completed" in analytics.allowed_events()
    assert "answer" not in analytics.allowed_events()

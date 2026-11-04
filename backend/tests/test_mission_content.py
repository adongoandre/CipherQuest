"""Content validation tests.

These are the automated guard the master prompt requires: a mission may not be
published unless its ciphertext is reproducible from the stored plaintext,
cipher and parameter.
"""

from __future__ import annotations

import pytest

from app.cipher import decrypt, encrypt, normalise_riddle_answer
from app.content import MISSION_DEFINITIONS, all_missions, apply_key_rule, validate_definition


def test_all_seed_missions_build_without_problems() -> None:
    for definition in MISSION_DEFINITIONS:
        assert validate_definition(definition) == [], (
            f"{definition.slug} failed content validation"
        )


def test_all_missions_returns_five_published_missions() -> None:
    missions = all_missions()
    assert len(missions) == 5
    assert len({m["slug"] for m in missions}) == 5
    assert [m["display_order"] for m in missions] == [1, 2, 3, 4, 5]


STORY_KEYS = (
    "narrative",
    "riddle_prompt",
    "accepted_riddle_answers",
    "key_rule_id",
    "key_rule_description",
    "key_type",
    "parameter",
    "contextual_clue",
    "ciphertext",
    "plaintext_answer",
    "hints",
    "comprehension_check",
    "explanation",
    "worked_example",
)


def tellings(mission: dict) -> list[dict]:
    """Every telling of a mission, each as a self-contained payload."""
    base = {key: mission[key] for key in STORY_KEYS}
    return [base, *mission["stories"]]


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_ciphertext_is_generated_from_plaintext_and_parameter(mission: dict) -> None:
    shift = mission["parameter"]
    assert 1 <= shift <= 25
    assert mission["ciphertext"] == encrypt(mission["plaintext_answer"], shift)
    assert decrypt(mission["ciphertext"], shift) == mission["plaintext_answer"]


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_parameter_follows_the_published_key_rule(mission: dict) -> None:
    for variant in mission["accepted_riddle_answers"]:
        assert apply_key_rule(mission["key_rule_id"], variant) == mission["parameter"]
    # The published rule description must be the registry text for that rule.
    from app.content.key_rules import KEY_RULE_DESCRIPTIONS

    assert mission["key_rule_description"] == KEY_RULE_DESCRIPTIONS[mission["key_rule_id"]]


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_contextual_clue_does_not_disclose_the_plaintext(mission: dict) -> None:
    for telling in tellings(mission):
        clue = telling["contextual_clue"].casefold()
        plaintext = telling["plaintext_answer"].casefold()
        assert clue != plaintext
        assert plaintext not in clue
        # ...and it must not simply hand over the ciphertext's first word either.
        first_word = plaintext.split()[0]
        assert first_word not in clue.split()


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_mission_has_three_progressive_hints(mission: dict) -> None:
    hints = mission["hints"]
    assert len(hints) == 3
    assert all(isinstance(h, str) and h.strip() for h in hints)
    assert len({h.casefold() for h in hints}) == 3
    # Hint 3 gives procedure; it must never state the plaintext.
    assert mission["plaintext_answer"].casefold() not in hints[2].casefold()


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_riddle_accepts_every_published_variant_only(mission: dict) -> None:
    variants = mission["accepted_riddle_answers"]
    for variant in variants:
        assert normalise_riddle_answer(variant, variants)
        assert normalise_riddle_answer(f"  {variant.upper()}  ", variants)
    assert not normalise_riddle_answer("", variants)
    assert not normalise_riddle_answer("definitely not the answer", variants)


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_explanation_and_worked_example_are_present(mission: dict) -> None:
    assert mission["explanation"].strip()
    assert mission["worked_example"].strip()
    assert str(mission["parameter"]) in mission["explanation"]
    assert "Caesar shift" in mission["explanation"]
    assert mission["worked_example"].count("=") >= 2


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_scoring_config_is_within_the_100_point_budget(mission: dict) -> None:
    cfg = mission["scoring_config"]
    total = cfg["solve_points"] + cfg["no_hint_bonus"] + cfg["comprehension_bonus"]
    assert total <= cfg["max_total"]
    assert cfg["solve_points"] + cfg["time_bonus_max"] + cfg["no_hint_bonus"] + cfg[
        "comprehension_bonus"
    ] == cfg["max_total"]


def test_difficulty_varies_across_missions() -> None:
    difficulties = {m["difficulty"] for m in all_missions()}
    assert difficulties >= {"beginner", "intermediate", "advanced"}


# --- alternative tellings -------------------------------------------------
# Every mission ships its original telling plus at least three alternatives,
# so a replay never repeats a story the player has already read. (The old
# "every shift is distinct" rule was retired with the old key system: shifts
# are now letter counts, which collide naturally across short answers.)


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_every_mission_has_at_least_four_distinct_tellings(mission: dict) -> None:
    all_tellings = tellings(mission)
    assert len(all_tellings) >= 4
    narratives = [t["narrative"] for t in all_tellings]
    riddles = [t["riddle_prompt"] for t in all_tellings]
    plaintexts = [t["plaintext_answer"] for t in all_tellings]
    assert len(set(narratives)) == len(narratives), "narratives must never repeat"
    assert len(set(riddles)) == len(riddles), "riddles must never repeat"
    assert len(set(plaintexts)) == len(plaintexts), "messages must never repeat"


@pytest.mark.parametrize("mission", all_missions(), ids=lambda m: m["slug"])
def test_every_telling_round_trips_and_follows_its_key_rule(mission: dict) -> None:
    for telling in tellings(mission):
        shift = telling["parameter"]
        assert 1 <= shift <= 25
        assert telling["ciphertext"] == encrypt(telling["plaintext_answer"], shift)
        assert decrypt(telling["ciphertext"], shift) == telling["plaintext_answer"]
        assert len(telling["ciphertext"]) == len(telling["plaintext_answer"])
        for variant in telling["accepted_riddle_answers"]:
            assert apply_key_rule(telling["key_rule_id"], variant) == shift
        assert len(telling["hints"]) == 3
        assert telling["comprehension_check"]["question"]


def test_shift_equals_the_letter_count_of_the_answer() -> None:
    """The player-visible key rule: shift == letters in the riddle answer."""
    for mission in all_missions():
        for telling in tellings(mission):
            answer = telling["accepted_riddle_answers"][0]
            letters = sum(1 for c in answer if c.isascii() and c.isalpha())
            assert telling["parameter"] == letters

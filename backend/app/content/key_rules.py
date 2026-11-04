"""Mission key rules.

The Riddle Key System requires an explicit, visible rule that converts the
riddle answer into a cipher parameter. A Caesar cipher takes a numeric shift —
never the word itself — so every rule here maps a *string answer* to an
integer in ``1..25``.

Rules are pure functions registered by id so that seeding and validation can
re-derive the parameter from the accepted riddle answers and fail loudly if a
mission's published parameter disagrees with its own rule.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

VOWELS: Final = frozenset("aeiou")


def letter_count(answer: str) -> int:
    """Number of ASCII letters in the answer (``"a clock"`` → 6)."""
    return sum(1 for char in answer if char.isascii() and char.isalpha())


def first_letter_position(answer: str) -> int:
    """1-based alphabet position of the first ASCII letter (``"candle"`` → 3)."""
    for char in answer:
        if char.isascii() and char.isalpha():
            return ord(char.upper()) - ord("A") + 1
    raise ValueError("answer contains no letters")


def vowel_count(answer: str) -> int:
    """Number of vowels in the answer, case-insensitively (``"fire"`` → 2)."""
    return sum(1 for char in answer if char in VOWELS or char.upper() in VOWELS)


KeyRule = Callable[[str], int]

KEY_RULES: Final[dict[str, KeyRule]] = {
    "letter_count": letter_count,
    "first_letter_position": first_letter_position,
    "vowel_count": vowel_count,
}

KEY_RULE_DESCRIPTIONS: Final[dict[str, str]] = {
    "letter_count": "Count the letters in your riddle answer. That number is the Caesar shift.",
    "first_letter_position": (
        "Take the position of the first letter of your riddle answer in the alphabet "
        "(A = 1, B = 2, … Z = 26). That number is the Caesar shift."
    ),
    "vowel_count": (
        "Count the vowels (A, E, I, O, U) in your riddle answer. "
        "That number is the Caesar shift."
    ),
}


def apply_key_rule(key_rule_id: str, answer: str) -> int:
    """Evaluate a registered key rule and return the resulting shift.

    Raises ``KeyError`` for an unknown rule and ``ValueError`` when the rule
    cannot produce a shift in the usable range ``1..25``.
    """
    try:
        rule = KEY_RULES[key_rule_id]
    except KeyError as exc:
        raise KeyError(f"unknown key rule: {key_rule_id!r}") from exc

    value = rule(answer)
    if not 1 <= value <= 25:
        raise ValueError(
            f"key rule {key_rule_id!r} produced {value} from {answer!r}; "
            "Caesar shifts must be 1..25 for a playable mission"
        )
    return value

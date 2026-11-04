"""Answer normalisation.

Policy (MVP Master Prompt §6):

* Outer whitespace is always trimmed.
* Comparison is case-insensitive by default.
* Internal whitespace is collapsed **only** when the mission's rules ask for it.
* Punctuation is meaningful and is never silently discarded.

Both functions are pure and side-effect free so they can be unit-tested
independently of the API layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MULTI_SPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class AnswerRules:
    """Normalisation policy for a mission's decrypt answer."""

    case_insensitive: bool = True
    collapse_internal_whitespace: bool = False
    strip_outer_whitespace: bool = True

    @classmethod
    def default(cls) -> "AnswerRules":
        return cls()


def _apply(text: str, rules: AnswerRules) -> str:
    if not isinstance(text, str):
        raise TypeError(f"answer must be a string, got {type(text).__name__}")
    value = text
    if rules.strip_outer_whitespace:
        value = value.strip()
    if rules.collapse_internal_whitespace:
        value = _MULTI_SPACE.sub(" ", value)
    if rules.case_insensitive:
        value = value.casefold()
    return value


def normalise_answer(text: str, rules: AnswerRules | None = None) -> str:
    """Normalise a submitted plaintext answer for comparison."""
    return _apply(text, rules or AnswerRules.default())


def answers_match(submitted: str, expected: str, rules: AnswerRules | None = None) -> bool:
    """Return ``True`` when ``submitted`` normalises to the expected plaintext."""
    policy = rules or AnswerRules.default()
    if not isinstance(expected, str):
        raise TypeError(f"expected must be a string, got {type(expected).__name__}")
    return normalise_answer(submitted, policy) == normalise_answer(expected, policy)


def normalise_riddle_answer(
    text: str,
    accepted_variants: list[str] | tuple[str, ...],
    *,
    case_insensitive: bool = True,
) -> bool:
    """Return ``True`` when ``text`` matches any accepted riddle variant.

    Matching is deliberately tight: outer whitespace is trimmed and case is
    ignored, but internal wording, spelling and punctuation must agree exactly
    so that unrelated words are never accepted.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a string, got {type(text).__name__}")
    if not accepted_variants:
        raise ValueError("accepted_variants must contain at least one variant")

    rules = AnswerRules(
        case_insensitive=case_insensitive,
        collapse_internal_whitespace=False,
        strip_outer_whitespace=True,
    )
    candidate = _apply(text, rules)
    if not candidate:
        return False
    return any(candidate == _apply(variant, rules) for variant in accepted_variants)

"""Unit tests for the Caesar cipher engine and answer normalisation."""

from __future__ import annotations

import pytest

from app.cipher import (
    AnswerRules,
    answers_match,
    decrypt,
    derive_shift_from_answer,
    encrypt,
    normalise_answer,
    normalise_riddle_answer,
    normalise_shift,
)


# --- known examples -------------------------------------------------------


@pytest.mark.parametrize(
    ("plaintext", "shift", "expected"),
    [
        ("ABC", 1, "BCD"),
        ("abc", 1, "bcd"),
        ("XYZ", 1, "YZA"),
        ("xyz", 1, "yza"),
        ("Hello, World!", 3, "Khoor, Zruog!"),
        ("ATTACKATDAWN", 3, "DWWDFNDWGDZQ"),
        ("abcxyz", 25, "zabwxy"),
    ],
)
def test_encrypt_known_examples(plaintext: str, shift: int, expected: str) -> None:
    assert encrypt(plaintext, shift) == expected


@pytest.mark.parametrize(
    ("ciphertext", "shift", "expected"),
    [
        ("BCD", 1, "ABC"),
        ("Khoor, Zruog!", 3, "Hello, World!"),
        ("DWWDFNDWGDZQ", 3, "ATTACKATDAWN"),
    ],
)
def test_decrypt_known_examples(ciphertext: str, shift: int, expected: str) -> None:
    assert decrypt(ciphertext, shift) == expected


# --- shift normalisation --------------------------------------------------


@pytest.mark.parametrize("shift", [0, 1, 15, 25, 26, 27, 52, 100, -1, -26, -27])
def test_shift_normalisation_is_mod_26(shift: int) -> None:
    assert normalise_shift(shift) == shift % 26
    assert 0 <= normalise_shift(shift) <= 25


@pytest.mark.parametrize("shift", [0, 1, 25, 26, 27, -1, -25, 51])
def test_equivalent_shifts_produce_identical_output(shift: int) -> None:
    assert encrypt("Mission Text 42!", shift) == encrypt("Mission Text 42!", shift % 26)


def test_shift_zero_is_identity() -> None:
    assert encrypt("No change here.", 0) == "No change here."
    assert decrypt("No change here.", 0) == "No change here."


def test_shift_26_is_identity() -> None:
    assert encrypt("Full rotation", 26) == "Full rotation"


def test_negative_shift_is_the_inverse_of_positive() -> None:
    assert encrypt("negative shift", -3) == decrypt("negative shift", 3)


@pytest.mark.parametrize("bad", [1.5, float("nan")])
def test_non_integer_shift_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        normalise_shift(bad)


def test_boolean_shift_rejected() -> None:
    with pytest.raises(TypeError):
        normalise_shift(True)  # type: ignore[arg-type]


def test_non_numeric_shift_rejected() -> None:
    with pytest.raises(TypeError):
        normalise_shift("3")  # type: ignore[arg-type]


def test_non_string_text_rejected() -> None:
    with pytest.raises(TypeError):
        encrypt(123, 3)  # type: ignore[arg-type]


# --- case, punctuation, whitespace ---------------------------------------


def test_case_is_preserved_not_swapped() -> None:
    assert encrypt("AbC", 1) == "BcD"


def test_spaces_and_punctuation_are_untouched() -> None:
    assert encrypt("a-b_c d.e!", 5) == "f-g_h i.j!"


def test_digits_are_untouched() -> None:
    assert encrypt("abc 123 xyz", 13) == "nop 123 klm"


def test_empty_string_round_trip() -> None:
    assert encrypt("", 7) == ""
    assert decrypt("", 7) == ""


def test_non_ascii_passthrough() -> None:
    # 'é' is outside A-Z/a-z so it is untouched while ASCII letters shift.
    assert encrypt("café", 1) == "dbgé"
    assert encrypt("日本語", 10) == "日本語"


def test_unicode_emoji_passthrough() -> None:
    assert encrypt("🔐 key", 2) == "🔐 mga"


# --- round trips ----------------------------------------------------------


@pytest.mark.parametrize("shift", list(range(-30, 31)))
@pytest.mark.parametrize(
    "text",
    [
        "",
        "a",
        "The quick brown fox jumps over the lazy dog.",
        "MIXED case with PUNCTUATION! and 123 numbers; ends here.",
        "xyzXYZ",
        "spaces   kept\tas\tis",
    ],
)
def test_encrypt_decrypt_round_trip(text: str, shift: int) -> None:
    assert decrypt(encrypt(text, shift), shift) == text


@pytest.mark.parametrize("shift", [1, 3, 13, 25])
def test_encrypt_then_decrypt_on_ciphertext(shift: int) -> None:
    plaintext = "Round trips are mandatory."
    assert decrypt(encrypt(plaintext, shift), shift) == plaintext
    # encrypting twice with complementary shifts is also the identity
    assert encrypt(encrypt(plaintext, shift), 26 - shift) == plaintext


# --- key derivation from riddle answer ------------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("CLOCK", 5),
        ("clock", 5),
        ("a clock", 6),
        ("CLOCK!", 5),
        ("  river  ", 5),
        ("MOON", 4),
        ("TREE", 4),
    ],
)
def test_derive_shift_counts_letters_only(answer: str, expected: int) -> None:
    assert derive_shift_from_answer(answer) == expected


def test_derive_shift_rejects_letterless_answer() -> None:
    with pytest.raises(ValueError):
        derive_shift_from_answer("123 !!!")


def test_derive_shift_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        derive_shift_from_answer(None)  # type: ignore[arg-type]


# --- answer normalisation -------------------------------------------------


@pytest.mark.parametrize(
    ("submitted", "expected", "rules", "matches"),
    [
        ("  Hello, World!  ", "Hello, World!", AnswerRules.default(), True),
        ("HELLO, WORLD!", "Hello, World!", AnswerRules.default(), True),
        ("hElLo, WoRlD!", "Hello, World!", AnswerRules.default(), True),
        ("Hello,  World!", "Hello, World!", AnswerRules.default(), False),
        ("Hello,  World!", "Hello, World!", AnswerRules(collapse_internal_whitespace=True), True),
        ("Hello World!", "Hello, World!", AnswerRules.default(), False),
        ("", "", AnswerRules.default(), True),
        ("", "answer", AnswerRules.default(), False),
        ("", "  ", AnswerRules.default(), True),
    ],
)
def test_answer_normalisation(
    submitted: str, expected: str, rules: AnswerRules, matches: bool
) -> None:
    assert answers_match(submitted, expected, rules) is matches


def test_normalise_answer_applies_casefold() -> None:
    assert normalise_answer("  THE MESSAGE  ") == "the message"


def test_punctuation_is_not_silently_discarded() -> None:
    assert not answers_match("its here", "it's here")
    assert answers_match("it's here", "it's here")


def test_answers_match_rejects_non_string_expected() -> None:
    with pytest.raises(TypeError):
        answers_match("x", None)  # type: ignore[arg-type]


# --- riddle answer variants -----------------------------------------------


@pytest.mark.parametrize(
    ("submitted", "variants", "expected"),
    [
        ("clock", ["clock", "a clock"], True),
        ("CLOCK", ["clock", "a clock"], True),
        ("  CLOCK  ", ["clock", "a clock"], True),
        ("clock?", ["clock", "a clock"], False),
        ("a clock", ["clock", "a clock"], True),
        ("A CLOCK", ["clock", "a clock"], True),
        ("an alarm clock", ["clock", "a clock"], False),
        ("", ["clock"], False),
        ("   ", ["clock"], False),
        ("river", ["clock"], False),
    ],
)
def test_riddle_answer_matching(submitted: str, variants: list[str], expected: bool) -> None:
    assert normalise_riddle_answer(submitted, variants) is expected


def test_riddle_matching_respects_case_sensitivity_flag() -> None:
    assert normalise_riddle_answer("CLOCK", ["clock"], case_insensitive=False) is False
    assert normalise_riddle_answer("clock", ["clock"], case_insensitive=False) is True


def test_riddle_requires_at_least_one_variant() -> None:
    with pytest.raises(ValueError):
        normalise_riddle_answer("clock", [])


def test_riddle_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        normalise_riddle_answer(42, ["clock"])  # type: ignore[arg-type]

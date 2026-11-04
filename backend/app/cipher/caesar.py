"""Caesar cipher — a pure, dependency-free transformation module.

Design rules (see MVP Master Prompt §6):

* Only ASCII ``A-Z`` / ``a-z`` are shifted. Spaces, digits, punctuation and any
  other character pass through untouched.
* Case policy: **case is preserved**. Uppercase letters shift within ``A-Z``,
  lowercase letters shift within ``a-z``. The alphabet is never mixed.
* Shifts are normalised modulo 26, so ``0``, ``26``, ``27``, ``-1`` and ``52``
  all behave predictably.
* ``decrypt(text, shift)`` is the exact inverse of ``encrypt(text, shift)``.

This module must never import from FastAPI, SQLAlchemy or any UI concern.
"""

from __future__ import annotations

ALPHABET_SIZE = 26
_UPPER_BASE = ord("A")
_LOWER_BASE = ord("a")


def normalise_shift(shift: int | float) -> int:
    """Reduce any numeric shift to its canonical range ``0..25``.

    Raises ``TypeError`` for non-numeric input and ``ValueError`` for booleans
    (``bool`` is an ``int`` subclass but is never an intentional shift).
    """
    if isinstance(shift, bool) or not isinstance(shift, (int, float)):
        raise TypeError(f"shift must be a number, got {type(shift).__name__}")
    if isinstance(shift, float):
        if not float(shift).is_integer():
            raise ValueError(f"shift must be a whole number, got {shift}")
        shift = int(shift)
    return int(shift) % ALPHABET_SIZE


def _shift_char(char: str, shift: int) -> str:
    code = ord(char)
    if "A" <= char <= "Z":
        return chr(_UPPER_BASE + (code - _UPPER_BASE + shift) % ALPHABET_SIZE)
    if "a" <= char <= "z":
        return chr(_LOWER_BASE + (code - _LOWER_BASE + shift) % ALPHABET_SIZE)
    return char


def encrypt(text: str, shift: int) -> str:
    """Shift every ASCII letter forward by ``shift`` (mod 26).

    Non-letters — spaces, digits, punctuation, unicode — are returned as-is.
    """
    if not isinstance(text, str):
        raise TypeError(f"text must be a string, got {type(text).__name__}")
    effective = normalise_shift(shift)
    if effective == 0:
        return text
    return "".join(_shift_char(char, effective) for char in text)


def decrypt(text: str, shift: int) -> str:
    """Reverse :func:`encrypt` exactly — decrypting with the same shift."""
    if not isinstance(text, str):
        raise TypeError(f"text must be a string, got {type(text).__name__}")
    effective = normalise_shift(shift)
    if effective == 0:
        return text
    return "".join(_shift_char(char, -effective) for char in text)


def derive_shift_from_answer(answer: str) -> int:
    """Apply the standard mission key rule: *letter count of the riddle answer*.

    Only ASCII letters are counted, so ``"a clock"`` yields 6 and ``"CLOCK!"``
    yields 5. An empty/letterless answer raises ``ValueError`` because no
    mission may publish a key rule that cannot produce a parameter.
    """
    if not isinstance(answer, str):
        raise TypeError(f"answer must be a string, got {type(answer).__name__}")
    count = sum(1 for char in answer if char.isascii() and char.isalpha())
    if count == 0:
        raise ValueError("cannot derive a Caesar shift from an answer with no letters")
    return count

"""Cipher engine package.

Keep this package free of API, ORM and UI imports: ciphers must remain
independently testable and reusable.
"""

from app.cipher.caesar import (
    ALPHABET_SIZE,
    decrypt,
    derive_shift_from_answer,
    encrypt,
    normalise_shift,
)
from app.cipher.normalise import (
    AnswerRules,
    answers_match,
    normalise_answer,
    normalise_riddle_answer,
)

__all__ = [
    "ALPHABET_SIZE",
    "AnswerRules",
    "answers_match",
    "decrypt",
    "derive_shift_from_answer",
    "encrypt",
    "normalise_answer",
    "normalise_riddle_answer",
    "normalise_shift",
]

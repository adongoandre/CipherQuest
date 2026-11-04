"""Mission content model.

Mission content is stored separately from presentation and from the cipher
engine. ``ciphertext`` is always generated from ``plaintext_answer`` +
``cipher_type`` + ``parameter`` by the seeding/validation command — it is never
hand-authored. ``plaintext_answer`` and ``accepted_riddle_answers`` are
**protected** and must never leave the server before the intended reveal.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CipherType(str, enum.Enum):
    CAESAR = "caesar"
    ATBASH = "atbash"  # deferred: P1 only, never published until all P0 pass


class Difficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PublicationStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"), nullable=False, default=Difficulty.BEGINNER
    )
    cipher_type: Mapped[CipherType] = mapped_column(
        Enum(CipherType, name="cipher_type"), nullable=False, default=CipherType.CAESAR
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # --- riddle + key rule -------------------------------------------------
    riddle_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_riddle_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    key_rule_description: Mapped[str] = mapped_column(Text, nullable=False)
    key_rule_id: Mapped[str] = mapped_column(String(40), nullable=False, default="letter_count")
    key_type: Mapped[str] = mapped_column(String(40), nullable=False, default="shift")
    parameter: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- clue + ciphertext -------------------------------------------------
    contextual_clue: Mapped[str] = mapped_column(Text, nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)

    # --- protected: never serialised before reveal ------------------------
    plaintext_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # --- alternative tellings ---------------------------------------------
    # Base columns above hold telling #1. This holds tellings #2..#N for the
    # same mission (at least three alternatives), each a full story payload
    # with the same keys as build_story_payload(). A player who has already
    # solved a mission is served the next telling on replay.
    stories: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )

    # --- teaching ----------------------------------------------------------
    hints: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    comprehension_check: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    worked_example: Mapped[str] = mapped_column(Text, nullable=False)

    # --- scoring -----------------------------------------------------------
    scoring_config: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, name="publication_status"),
        nullable=False,
        default=PublicationStatus.DRAFT,
        index=True,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def hint_count(self) -> int:
        return len(self.hints or [])

    @property
    def telling_count(self) -> int:
        """Number of tellings stored for this mission (original + alternates)."""
        return 1 + len(self.stories or [])

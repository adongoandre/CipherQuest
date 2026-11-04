"""Academy lesson progress: one row per (session, cipher, step) completed."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("session_id", "cipher_slug", "step", name="uq_lesson_step"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cipher_slug: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    # XP is granted exactly once, on first completion of the step.
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

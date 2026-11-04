"""Feedback and analytics models.

Analytics events are deliberately privacy-conscious: they store an event name,
the pseudonymous session id, a timestamp and a small set of non-sensitive
properties. Raw typed answers are never recorded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    clarity_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    learned: Mapped[str | None] = mapped_column(String(10), nullable=True)
    enjoyment_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    would_return: Mapped[str | None] = mapped_column(String(10), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mission_id: Mapped[int | None] = mapped_column(
        ForeignKey("missions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

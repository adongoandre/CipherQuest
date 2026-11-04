"""Weekly Free Cup entries and the mission-editor audit trail."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CupEntry(Base):
    """One player's entry into a week's cup. Week keys look like ``2026-W44``."""

    __tablename__ = "cup_entries"
    __table_args__ = (UniqueConstraint("session_id", "week", name="uq_cup_entry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    """Append-only record of admin mission-editor actions."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, default="mission")
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

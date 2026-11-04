"""Guest/player session model.

The MVP uses a lightweight pseudonymous session rather than full accounts.
Only the minimum data needed to persist progress is stored: an opaque token
and an optional display name. No IP address is retained.

A guest may later upgrade in place (Join screen) by adding an email and
password hash, keeping all progress; accessibility/privacy preferences from
the Settings screen live in ``preferences``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def new_session_token() -> str:
    return uuid.uuid4().hex


class PlayerSession(Base):
    __tablename__ = "player_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, default=new_session_token
    )
    display_name: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # --- optional account (Join screen) -----------------------------------
    email: Mapped[str | None] = mapped_column(
        String(254), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # --- settings (accessibility / privacy / play style) ------------------
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

"""Friends, duels, blocks and reports.

Friendships are symmetric once accepted; the requester/addressee pair is only
meaningful while an invitation is pending. A block is absolute: a blocked
session never sees the other in friends, invitations or leaderboards.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"


class DuelInviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friend_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, name="friendship_status"),
        nullable=False,
        default=FriendshipStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DuelInvite(Base):
    __tablename__ = "duel_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[DuelInviteStatus] = mapped_column(
        Enum(DuelInviteStatus, name="duel_invite_status"),
        nullable=False,
        default=DuelInviteStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_block_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blocker_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    blocked_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

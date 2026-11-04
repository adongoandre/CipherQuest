"""Friends, invitations, blocks and reports (Home + Play social sections)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FriendEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    display_name: str
    level: int
    status: Literal["offline", "recently_active"] = "offline"


class InvitationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    from_display_name: str
    kind: Literal["cipher_duel"] = "cipher_duel"
    created_at: datetime


class FriendRequestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int  # friendship row id, used by /friends/respond
    display_name: str
    level: int
    created_at: datetime


class BlockedEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    display_name: str


class FriendsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    friends: list[FriendEntry]
    invitations: list[InvitationEntry]
    pending_outgoing: list[InvitationEntry]
    blocked: list[BlockedEntry]
    requests_incoming: list[FriendRequestEntry]
    requests_outgoing: list[FriendRequestEntry]


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=60)


class FriendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=60)


class RespondRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invite_id: int
    action: Literal["accept", "decline"]


class FriendRespondRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    friendship_id: int
    action: Literal["accept", "decline"]


class BlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=60)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=60)
    reason: str = Field(min_length=3, max_length=500)


class ActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str
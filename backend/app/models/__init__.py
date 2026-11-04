"""ORM models.

Importing this package registers every table on ``Base.metadata``, which is
required before ``Base.metadata.create_all`` or Alembic autogenerate runs.
"""

from app.models.attempt import Attempt, AttemptOutcome, AttemptStage, Progress
from app.models.compete import AuditLog, CupEntry
from app.models.engagement import AnalyticsEvent, Feedback
from app.models.lesson import LessonProgress
from app.models.mission import CipherType, Difficulty, Mission, PublicationStatus
from app.models.room import Room, RoomMode, RoomPlayer, RoomStatus
from app.models.session import PlayerSession, new_session_token
from app.models.social import (
    Block,
    DuelInvite,
    DuelInviteStatus,
    Friendship,
    FriendshipStatus,
    Report,
)

__all__ = [
    "AnalyticsEvent",
    "Attempt",
    "AttemptOutcome",
    "AttemptStage",
    "AuditLog",
    "Block",
    "CipherType",
    "CupEntry",
    "Difficulty",
    "DuelInvite",
    "DuelInviteStatus",
    "Feedback",
    "Friendship",
    "FriendshipStatus",
    "LessonProgress",
    "Mission",
    "PlayerSession",
    "Progress",
    "PublicationStatus",
    "Report",
    "Room",
    "RoomMode",
    "RoomPlayer",
    "RoomStatus",
    "new_session_token",
]

"""Idempotent mission seeding.

Seeding upserts on ``slug`` so it is safe to run repeatedly. Ciphertext comes
from :func:`app.content.missions.build_mission`, which derives it from the
stored plaintext, cipher and parameter — a hand-written ciphertext can never
reach the database through this path.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content import all_missions
from app.models import (
    Friendship,
    FriendshipStatus,
    LessonProgress,
    Mission,
    PlayerSession,
    Progress,
    PublicationStatus,
)

logger = logging.getLogger(__name__)

# Demo players give the leaderboards, cup standings and friend feed real data
# on a fresh database. Scores are mirrored from the UI mockups.
DEMO_PLAYERS: list[tuple[str, int]] = [
    ("Maya", 460),
    ("Kofi", 415),
    ("Ama", 390),
    ("Yaw", 350),
]

# XP for each demo player's first Caesar lesson. It counts toward leaderboards,
# so mission XP only carries the remainder of the target score.
LESSON_XP = 5


def seed_missions(db: Session) -> dict[str, int]:
    """Insert or update every seed mission. Returns counters."""
    created = 0
    updated = 0

    for payload in all_missions():
        row = db.scalar(select(Mission).where(Mission.slug == payload["slug"]))
        if row is None:
            db.add(Mission(**_to_columns(payload)))
            created += 1
        else:
            for key, value in _to_columns(payload).items():
                setattr(row, key, value)
            updated += 1

    db.commit()
    logger.info(
        "mission seed complete",
        extra={"missions_created": created, "missions_updated": updated},
    )
    return {"created": created, "updated": updated}


def _to_columns(payload: dict) -> dict:
    """Map content payload keys onto Mission columns, converting enums."""
    from app.models import CipherType, Difficulty, PublicationStatus as Status

    data = dict(payload)
    data["difficulty"] = Difficulty(data["difficulty"])
    data["cipher_type"] = CipherType(data["cipher_type"])
    data["status"] = Status(data.get("status", "published"))
    return data


def mission_count(db: Session) -> int:
    return int(db.scalar(select(func.count(Mission.id))) or 0)


def ensure_seeded(db: Session) -> bool:
    """Seed when the table is empty. Returns ``True`` if seeding happened."""
    if mission_count(db) == 0:
        seed_missions(db)
        return True
    return False


def ensure_demo_players(db: Session) -> bool:
    """Seed demo players (idempotent by display name) with mission progress."""
    from datetime import datetime, timedelta, timezone

    from app.services.compete import current_week

    if db.scalar(select(PlayerSession.id).where(PlayerSession.display_name == "Maya")) is not None:
        return False

    missions = list(
        db.scalars(
            select(Mission)
            .where(Mission.status == PublicationStatus.PUBLISHED)
            .order_by(Mission.display_order, Mission.id)
        )
    )
    if not missions:
        return False

    now = datetime.now(timezone.utc)
    created: list[PlayerSession] = []
    for name, target_xp in DEMO_PLAYERS:
        player = PlayerSession(
            display_name=name,
            email=f"{name.lower()}@demo.cipherquest.invalid",
            preferences={"privacy": {"show_display_name": True}},
        )
        db.add(player)
        db.flush()
        created.append(player)

        remaining = target_xp - LESSON_XP
        for index, mission in enumerate(missions):
            if remaining <= 0:
                break
            grant = min(95, remaining)
            if index == len(missions) - 1 and remaining < grant:
                grant = remaining
            remaining -= grant
            db.add(
                Progress(
                    session_id=player.id,
                    mission_id=mission.id,
                    completion_count=1,
                    best_score=grant,
                    xp_awarded=grant,
                    completed_at=now - timedelta(hours=index + 1),
                    updated_at=now - timedelta(hours=index + 1),
                )
            )
        # The first lesson of the Caesar track, so Academy shows progress.
        db.add(
            LessonProgress(
                session_id=player.id,                    cipher_slug="caesar",
                    step=1,
                    xp_awarded=LESSON_XP,
            )
        )

    # A friendly social graph: everyone knows everyone.
    for i, a in enumerate(created):
        for b in created[i + 1 :]:
            db.add(
                Friendship(
                    requester_id=a.id,
                    addressee_id=b.id,
                    status=FriendshipStatus.ACCEPTED,
                )
            )

    # Enter every demo player in the current week's cup.
    from app.models import CupEntry

    week = current_week(now)
    for player in created:
        db.add(CupEntry(session_id=player.id, week=week))

    db.commit()
    logger.info("seeded demo players", extra={"players": [p.display_name for p in created]})
    return True


def published_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(Mission.id)).where(
                Mission.status == PublicationStatus.PUBLISHED
            )
        )
        or 0
    )

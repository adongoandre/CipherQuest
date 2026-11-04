"""Privacy-conscious analytics.

Only the event name, the pseudonymous session id, an optional mission id and a
small set of non-sensitive properties are stored. Raw typed answers are never
recorded — outcomes only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, Mission, PlayerSession

ALLOWED_EVENTS = frozenset(
    {
        "landing_view",
        "mission_started",
        "mission_restarted",
        "riddle_submitted",
        "key_revealed",
        "context_clue_viewed",
        "hint_used",
        "decrypt_submitted",
        "mission_completed",
        "solution_revealed",
        "next_mission_clicked",
        "feedback_submitted",
        "comprehension_answered",
    }
)

# Property keys that must never be accepted, guarding against accidental
# capture of typed answers or personal data.
FORBIDDEN_KEYS = frozenset({"answer", "plaintext", "comment", "email", "name", "token"})


def record(
    db: Session,
    event_name: str,
    *,
    session: PlayerSession | None = None,
    mission: Mission | None = None,
    **properties: Any,
) -> AnalyticsEvent | None:
    """Persist one analytics event, failing closed on disallowed input."""
    if event_name not in ALLOWED_EVENTS:
        raise ValueError(f"unknown analytics event: {event_name!r}")

    clean = {k: v for k, v in properties.items() if k not in FORBIDDEN_KEYS}
    if any(k in FORBIDDEN_KEYS for k in properties):
        raise ValueError("analytics properties must not carry raw answers or personal data")

    event = AnalyticsEvent(
        event_name=event_name,
        session_id=session.id if session else None,
        mission_id=mission.id if mission else None,
        properties=clean,
    )
    db.add(event)
    return event


def allowed_events() -> list[str]:
    return sorted(ALLOWED_EVENTS)


def recent(db: Session, event_name: str, limit: int = 50) -> list[AnalyticsEvent]:
    stmt = (
        select(AnalyticsEvent)
        .where(AnalyticsEvent.event_name == event_name)
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))

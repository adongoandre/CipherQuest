"""Leaderboards and the Weekly Free Cup.

Scores are XP earned inside the scope's window. The cup runs every ISO week
from Saturday 10:00 UTC to Sunday 20:00 UTC; entering any time before close
scores the player from the week's XP (any week XP counts, so entering late
still works). Rank ``change`` is only known where a comparable prior window
exists (the ``week`` scope compares this week to last week).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models import (
    Friendship,
    FriendshipStatus,
    LessonProgress,
    PlayerSession,
    Progress,
    CupEntry,
    Block,
)
from app.schemas.compete import (
    CupState,
    LeaderboardResponse,
    StandingEntry,
    YourPosition,
)

SEASON_DAYS = 30
DAILY_LESSON_XP = 5
CUP_LABEL = "Saturday 10:00 – Sunday 20:00 (UTC)"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- score helpers ---------------------------------------------------------

def _xp_sum(db: DbSession, session_ids: list[int] | None, since: datetime | None) -> int:
    """Total XP (missions + lessons) for the given sessions since ``since``."""
    mission_q = select(func.coalesce(func.sum(Progress.xp_awarded), 0))
    lesson_q = select(func.coalesce(func.sum(LessonProgress.xp_awarded), 0))
    if session_ids is not None:
        mission_q = mission_q.where(Progress.session_id.in_(session_ids))
        lesson_q = lesson_q.where(LessonProgress.session_id.in_(session_ids))
    if since is not None:
        mission_q = mission_q.where(Progress.updated_at >= since)
        lesson_q = lesson_q.where(LessonProgress.completed_at >= since)
    mission = int(db.scalar(mission_q) or 0)
    lesson = int(db.scalar(lesson_q) or 0)
    return mission + lesson


def _visible_sessions(db: DbSession) -> list[PlayerSession]:
    """Players who opted into leaderboards and have a name to show."""
    return list(db.scalars(select(PlayerSession)))


def _scope_ids(db: DbSession, viewer: PlayerSession, scope: str) -> list[int] | None:
    """Session ids to rank, or None for "everyone"."""
    if scope == "friends":
        rows = db.execute(
            select(Friendship.requester_id, Friendship.addressee_id).where(
                Friendship.status == FriendshipStatus.ACCEPTED,
                (Friendship.requester_id == viewer.id) | (Friendship.addressee_id == viewer.id),
            )
        ).all()
        ids = set()
        for a, b in rows:
            ids.add(a)
            ids.add(b)
        ids.add(viewer.id)
        # Never rank someone the viewer has blocked (or who blocked the viewer).
        blocked = db.execute(
            select(Block.blocker_id, Block.blocked_id).where(
                (Block.blocker_id == viewer.id) | (Block.blocked_id == viewer.id)
            )
        ).all()
        for a, b in blocked:
            ids.discard(a if a != viewer.id else b)
            ids.discard(b if b != viewer.id else a)
            ids.discard(b if a == viewer.id else a)
        return sorted(ids)
    return None


def _window_start(scope: str, now: datetime | None = None) -> datetime | None:
    now = now or _utcnow()
    if scope == "week":
        return now - timedelta(days=7)
    if scope == "season":
        return now - timedelta(days=SEASON_DAYS)
    return None


def _ranked(
    db: DbSession,
    scope: str,
    viewer: PlayerSession,
    *,
    since: datetime | None,
    ids: list[int] | None,
) -> list[tuple[PlayerSession, int, int]]:
    """Return (session, xp, missions) rows sorted by xp desc, name asc."""
    rows: list[tuple[PlayerSession, int, int]] = []
    for session in _visible_sessions(db):
        prefs = session.preferences or {}
        if not prefs.get("privacy", {}).get("show_display_name", True):
            # Anonymous players still appear, but never under their own name.
            pass
        if ids is not None and session.id not in ids:
            continue
        score = _xp_sum(db, [session.id], since)
        missions = _mission_count(db, session.id, since)
        if score <= 0 and missions <= 0:
            continue
        rows.append((session, score, missions))
    rows.sort(key=lambda row: (-row[1], -row[2], (row[0].display_name or "").lower()))
    return rows


def _mission_count(db: DbSession, session_id: int, since: datetime | None) -> int:
    q = select(func.count(Progress.id)).where(
        Progress.session_id == session_id, Progress.completion_count > 0
    )
    if since is not None:
        q = q.where(Progress.updated_at >= since)
    return int(db.scalar(q) or 0)


def _display(session: PlayerSession, viewer: PlayerSession) -> str:
    if session.id == viewer.id:
        return session.display_name or "You"
    prefs = session.preferences or {}
    if not prefs.get("privacy", {}).get("show_display_name", True):
        return "Anonymous decoder"
    return session.display_name or "Guest"


def build_leaderboard(db: DbSession, viewer: PlayerSession, scope: str) -> LeaderboardResponse:
    since = _window_start(scope)
    ids = _scope_ids(db, viewer, scope)
    rows = _ranked(db, scope, viewer, since=since, ids=ids)

    # Rank change: only meaningful for the weekly scope (this week vs last).
    changes: dict[int, int] = {}
    if scope == "week":
        prior_since = since - timedelta(days=7) if since else None
        prior = _ranked(db, "all_time", viewer, since=prior_since, ids=ids)
        prior_rank = {s.id: i + 1 for i, (s, _score, _m) in enumerate(prior)}
        for i, (session, _score, _m) in enumerate(rows):
            before = prior_rank.get(session.id)
            if before is not None:
                changes[session.id] = before - (i + 1)

    standings: list[StandingEntry] = []
    your_position: YourPosition | None = None
    for index, (session, score, missions) in enumerate(rows[:50], start=1):
        is_you = session.id == viewer.id
        standings.append(
            StandingEntry(
                rank=index,
                display_name=_display(session, viewer),
                score=score,
                missions=missions,
                change=changes.get(session.id),
                is_you=is_you,
            )
        )
        if is_you:
            gap = 0
            next_name = None
            if index > 1:
                above = rows[index - 2]
                gap = max(0, above[1] - score + 1)
                next_name = _display(above[0], viewer)
            your_position = YourPosition(
                rank=index, score=score, missions=missions,
                gap_to_next=gap, next_rank_name=next_name,
            )

    footers = {
        "week": "Rolling 7-day XP. Display names only — opt out in Settings.",
        "friends": "You and your accepted friends, all-time XP.",
        "season": f"Last {SEASON_DAYS} days of XP.",
        "all_time": "All-time XP. Display names only — opt out in Settings.",
    }
    return LeaderboardResponse(
        scope=scope,  # type: ignore[arg-type]
        standings=standings,
        you=your_position,
        footer=footers.get(scope, ""),
        total_players=len(rows),
    )


# --- weekly cup ------------------------------------------------------------

def _next_saturday_10(now: datetime) -> datetime:
    days = (5 - now.weekday()) % 7
    candidate = (now + timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def cup_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """The current cup window: the ongoing one, else the next scheduled one."""
    now = now or _utcnow()
    this_saturday = (now - timedelta(days=now.weekday() - 5)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    if now.weekday() == 5 and now >= this_saturday:
        opens = this_saturday
    elif now.weekday() == 6:
        saturday = now - timedelta(days=1)
        opens = saturday.replace(hour=10, minute=0, second=0, microsecond=0)
        if now < opens:
            opens = _next_saturday_10(now)
    else:
        opens = _next_saturday_10(now)
    return opens, opens + timedelta(days=1, hours=10)


def current_week(now: datetime | None = None) -> str:
    now = now or _utcnow()
    iso_year, iso_week, _ = now.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def build_cup(db: DbSession, viewer: PlayerSession) -> CupState:
    now = _utcnow()
    opens, closes = cup_window(now)
    status = "open" if opens <= now < closes else "scheduled"
    if now >= closes:
        # Between Sunday 20:00 and the next Saturday the event is scheduled.
        opens, closes = cup_window(now)
        status = "open" if opens <= now < closes else "scheduled"

    week = current_week(now)
    entered = db.scalar(
        select(CupEntry.id).where(CupEntry.session_id == viewer.id, CupEntry.week == week)
    )
    entrants = list(db.scalars(select(CupEntry).where(CupEntry.week == week)))
    entrant_ids = [e.session_id for e in entrants]

    rows: list[tuple[PlayerSession, int, int]] = []
    if entrant_ids:
        for session in _visible_sessions(db):
            if session.id not in entrant_ids:
                continue
            score = _xp_sum(db, [session.id], None)
            rows.append((session, score, _mission_count(db, session.id, None)))
        rows.sort(key=lambda r: (-r[1], -r[2], (r[0].display_name or "").lower()))

    standings: list[StandingEntry] = []
    your_position = None
    for index, (session, score, missions) in enumerate(rows, start=1):
        is_you = session.id == viewer.id
        standings.append(
            StandingEntry(
                rank=index, display_name=_display(session, viewer),
                score=score, missions=missions, is_you=is_you,
            )
        )
        if is_you:
            gap = 0
            next_name = None
            if index > 1:
                above = rows[index - 2]
                gap = max(0, above[1] - score + 1)
                next_name = _display(above[0], viewer)
            your_position = YourPosition(
                rank=index, score=score, missions=missions,
                gap_to_next=gap, next_rank_name=next_name,
            )

    your_score = _xp_sum(db, [viewer.id], None)
    seconds_open = int((opens - now).total_seconds())
    seconds_close = int((closes - now).total_seconds())
    return CupState(
        week=week,
        label=CUP_LABEL,
        status=status,
        opens_at=opens,
        closes_at=closes,
        seconds_until_open=max(0, seconds_open),
        seconds_until_close=max(0, seconds_close),
        participants=len(entrants),
        you_entered=entered is not None,
        your_score=your_score,
        standings=standings,
        you=your_position,
        note="Free entry. Your best week decides the podium.",
    )


def enter_cup(db: DbSession, viewer: PlayerSession) -> tuple[bool, str, str]:
    """Idempotent entry. Returns (entered, week, message)."""
    week = current_week()
    existing = db.scalar(
        select(CupEntry).where(CupEntry.session_id == viewer.id, CupEntry.week == week)
    )
    if existing is not None:
        return True, week, "You are already entered in this week's cup."
    db.add(CupEntry(session_id=viewer.id, week=week))
    db.commit()
    return True, week, "You're in. Solve missions this week to climb the standings."


__all__ = [
    "build_cup",
    "build_leaderboard",
    "current_week",
    "cup_window",
    "enter_cup",
]
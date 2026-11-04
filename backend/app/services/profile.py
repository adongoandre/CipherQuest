"""Profile, level, streak, badge, mastery and preference helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.content.curriculum import TRACKS
from app.models import (
    Attempt,
    AttemptOutcome,
    CupEntry,
    LessonProgress,
    Mission,
    PlayerSession,
    Progress,
    PublicationStatus,
)
from app.schemas.account import (
    Badge,
    CipherMastery,
    ProfileResponse,
    RecentMission,
)

XP_PER_LEVEL = 200
LESSON_XP = 5

DEFAULT_ACCESSIBILITY: dict[str, bool] = {
    "high_contrast_text": False,
    "reduce_motion": False,
    "dyslexic_friendly_font": False,
    "larger_text": False,
    "sound_effects": False,
}
DEFAULT_PRIVACY: dict[str, bool] = {
    "show_display_name": True,
    "anonymous_leaderboards": False,
    "share_anonymous_data": True,
}
DEFAULT_PLAY_STYLE: dict[str, bool] = {
    "timed_challenges": True,
    "daily_reminder": False,
}
PREFERENCE_GROUPS = {
    "accessibility": DEFAULT_ACCESSIBILITY,
    "privacy": DEFAULT_PRIVACY,
    "play_style": DEFAULT_PLAY_STYLE,
}


def level_for_xp(xp: int) -> tuple[int, int, int]:
    """Return ``(level, level_floor, level_ceiling)`` for a total XP value."""
    level = xp // XP_PER_LEVEL + 1
    return level, (level - 1) * XP_PER_LEVEL, level * XP_PER_LEVEL


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def activity_days(db: DbSession, session: PlayerSession) -> set[date]:
    """Every UTC day this session touched a mission or a lesson."""
    days: set[date] = set()
    for stamp in db.scalars(
        select(Attempt.created_at).where(Attempt.session_id == session.id)
    ):
        days.add(stamp.astimezone(timezone.utc).date())
    for stamp in db.scalars(
        select(Progress.completed_at).where(
            Progress.session_id == session.id, Progress.completed_at.is_not(None)
        )
    ):
        days.add(stamp.astimezone(timezone.utc).date())
    for stamp in db.scalars(
        select(LessonProgress.completed_at).where(LessonProgress.session_id == session.id)
    ):
        days.add(stamp.astimezone(timezone.utc).date())
    return days


def streak_from_days(days: set[date], today: date | None = None) -> tuple[int, int]:
    """Return ``(current_streak, longest_streak)`` from a set of active days."""
    if not days:
        return 0, 0
    today = today or _utc_today()
    start = today if today in days else today - timedelta(days=1)
    current = 0
    cursor = start
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    ordered = sorted(days)
    longest = run = 1
    for previous, nxt in zip(ordered, ordered[1:]):
        run = run + 1 if (nxt - previous).days == 1 else 1
        longest = max(longest, run)
    return current, max(current, longest)


def lesson_xp(db: DbSession, session: PlayerSession) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.coalesce(func.sum(LessonProgress.xp_awarded), 0)).where(
                LessonProgress.session_id == session.id
            )
        )
        or 0
    )


def mission_xp(db: DbSession, session: PlayerSession) -> int:
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.coalesce(func.sum(Progress.xp_awarded), 0)).where(
                Progress.session_id == session.id
            )
        )
        or 0
    )


def total_xp(db: DbSession, session: PlayerSession) -> int:
    return mission_xp(db, session) + lesson_xp(db, session)


def _completed_progress(db: DbSession, session: PlayerSession) -> list[Progress]:
    return list(
        db.scalars(
            select(Progress).where(
                Progress.session_id == session.id, Progress.completion_count > 0
            )
        )
    )


def accuracy_percent(db: DbSession, session: PlayerSession) -> int:
    outcomes = list(
        db.scalars(
            select(Attempt.outcome).where(
                Attempt.session_id == session.id,
                Attempt.outcome.in_([AttemptOutcome.CORRECT, AttemptOutcome.INCORRECT]),
            )
        )
    )
    if not outcomes:
        return 0
    correct = sum(1 for outcome in outcomes if outcome == AttemptOutcome.CORRECT)
    return round(100 * correct / len(outcomes))


def _build_badges(
    db: DbSession, session: PlayerSession, streak: int, completed: list[Progress]
) -> list[Badge]:
    caesar_total = int(
        db.scalar(
            select(func.count(Mission.id)).where(
                Mission.status == PublicationStatus.PUBLISHED,
                Mission.cipher_type == "caesar",
            )
        )
        or 0
    )
    caesar_done = 0
    if caesar_total:
        caesar_done = int(
            db.scalar(
                select(func.count(Progress.id))
                .join(Mission, Mission.id == Progress.mission_id)
                .where(
                    Progress.session_id == session.id,
                    Progress.completion_count > 0,
                    Mission.cipher_type == "caesar",
                )
            )
            or 0
        )
    lessons_done = int(
        db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.session_id == session.id
            )
        )
        or 0
    )
    cup_entered = (
        db.scalar(select(CupEntry.id).where(CupEntry.session_id == session.id)) is not None
    )

    def badge(key: str, name: str, description: str, earned: bool) -> Badge:
        return Badge(key=key, name=name, description=description, earned=earned)

    return [
        badge("first_decode", "First Decode", "Complete your first mission.", bool(completed)),
        badge("three_day_streak", "3-Day Streak", "Play on three consecutive days.", streak >= 3),
        badge("week_streak", "Week Streak", "Play on seven consecutive days.", streak >= 7),
        badge(
            "caesar_master",
            "Caesar Master",
            "Complete every published Caesar mission.",
            bool(caesar_total) and caesar_done >= caesar_total,
        ),
        badge("cup_contender", "Cup Contender", "Enter a Weekly Free Cup.", cup_entered),
        badge("lesson_starter", "Lesson Starter", "Finish your first Academy lesson.", lessons_done >= 1),
    ]


def build_mastery(db: DbSession, session: PlayerSession) -> list[CipherMastery]:
    from sqlalchemy import func

    counts: dict[str, int] = {}
    rows = db.execute(
        select(LessonProgress.cipher_slug, func.count(LessonProgress.id))
        .where(LessonProgress.session_id == session.id)
        .group_by(LessonProgress.cipher_slug)
    )
    for slug, count in rows:
        counts[str(slug)] = int(count)
    return [
        CipherMastery(
            cipher=track.slug,
            name=track.name,
            lessons_completed=counts.get(track.slug, 0),
            lessons_total=5,
        )
        for track in TRACKS
    ]


def recent_missions(db: DbSession, session: PlayerSession) -> list[RecentMission]:
    from sqlalchemy import func

    rows = db.execute(
        select(Mission, Progress)
        .join(Progress, Progress.mission_id == Mission.id)
        .where(Progress.session_id == session.id, Progress.completion_count > 0)
        .order_by(func.max(Progress.updated_at).desc())
        .group_by(Mission.id, Progress.id)
        .limit(4)
    ).all()
    return [
        RecentMission(
            slug=mission.slug,
            title=mission.title,
            best_score=progress.best_score,
            completed_at=progress.completed_at,
        )
        for mission, progress in rows
    ]


def build_profile(db: DbSession, session: PlayerSession) -> ProfileResponse:
    completed = _completed_progress(db, session)
    xp = total_xp(db, session)
    level, floor, ceiling = level_for_xp(xp)
    current_streak, longest_streak = streak_from_days(activity_days(db, session))

    from sqlalchemy import func as _func

    hints_used = int(
        db.scalar(
            select(_func.coalesce(_func.sum(Progress.hints_used_best), 0)).where(
                Progress.session_id == session.id
            )
        )
        or 0
    )
    scores = [p.best_score for p in completed if p.best_score]
    average_score = round(sum(scores) / len(scores)) if scores else 0

    completed_ids = [p.mission_id for p in completed]
    time_minutes = 0
    if completed_ids:
        time_minutes = int(
            db.scalar(
                select(_func.coalesce(_func.sum(Mission.estimated_minutes), 0)).where(
                    Mission.id.in_(completed_ids)
                )
            )
            or 0
        )

    return ProfileResponse(
        display_name=session.display_name or "Guest",
        is_guest=session.password_hash is None,
        is_admin=session.is_admin,
        level=level,
        xp=xp,
        level_ceiling=ceiling,
        level_floor=floor,
        missions_solved=len(completed),
        streak_days=current_streak,
        longest_streak=longest_streak,
        accuracy=accuracy_percent(db, session),
        hints_used=hints_used,
        average_score=average_score,
        time_played_minutes=time_minutes,
        badges=_build_badges(db, session, current_streak, completed),
        mastery=build_mastery(db, session),
        recent_missions=recent_missions(db, session),
        joined_at=session.created_at,
    )


def preferences_of(session: PlayerSession) -> dict[str, dict[str, bool]]:
    stored = session.preferences or {}
    merged: dict[str, dict[str, bool]] = {}
    for group, defaults in PREFERENCE_GROUPS.items():
        incoming = stored.get(group) or {}
        merged[group] = {
            key: bool(incoming.get(key, default)) for key, default in defaults.items()
        }
    return merged


def merge_preferences(
    session: PlayerSession,
    *,
    accessibility: dict[str, bool] | None = None,
    privacy: dict[str, bool] | None = None,
    play_style: dict[str, bool] | None = None,
) -> dict[str, dict[str, bool]]:
    current = preferences_of(session)
    for group, incoming in (
        ("accessibility", accessibility),
        ("privacy", privacy),
        ("play_style", play_style),
    ):
        if incoming is None:
            continue
        for key in current[group]:
            if key in incoming:
                current[group][key] = bool(incoming[key])
    session.preferences = current
    return current


__all__ = [
    "DEFAULT_ACCESSIBILITY",
    "DEFAULT_PLAY_STYLE",
    "DEFAULT_PRIVACY",
    "PREFERENCE_GROUPS",
    "XP_PER_LEVEL",
    "LESSON_XP",
    "activity_days",
    "accuracy_percent",
    "build_mastery",
    "build_profile",
    "level_for_xp",
    "merge_preferences",
    "mission_xp",
    "preferences_of",
    "recent_missions",
    "streak_from_days",
    "total_xp",
]
"""Home dashboard: daily mission, streak, cup, learning and friend signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.content.curriculum import TRACK_BY_SLUG, TRACKS
from app.models import (
    DuelInvite,
    DuelInviteStatus,
    LessonProgress,
    Mission,
    PlayerSession,
    Progress,
    PublicationStatus,
)
from app.schemas.compete import CupState
from app.services.compete import build_cup
from app.services.missions import daily_mission, published_missions
from app.services.profile import activity_days, build_profile, level_for_xp, streak_from_days, total_xp

router = APIRouter(tags=["home"])


class DailyMissionCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    difficulty: str
    cipher_name: str
    estimated_minutes: int
    completed: bool
    best_score: int | None = None


class ProgressStrip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: int
    xp: int
    level_ceiling: int
    streak_days: int
    missions_solved: int


class ContinueLearning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cipher_slug: str
    cipher_name: str
    step: int
    total_steps: int
    title: str


class InvitationCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    from_display_name: str
    kind: str = "cipher_duel"


class FriendActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    action: str
    when: datetime | None = None


class HomeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    greeting: str
    progress: ProgressStrip
    daily_mission: DailyMissionCard | None
    week_dots: list[bool]  # Mon..Sun activity for the current week
    weekly_cup: CupState
    continue_learning: ContinueLearning | None
    invitations: list[InvitationCard]
    friend_activity: list[FriendActivity]
    suggested_next: str | None = None


def _week_dots(db: DbSession, session: PlayerSession) -> list[bool]:
    """Monday..Sunday activity flags for the current UTC week."""
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    active = activity_days(db, session)
    return [(monday + timedelta(days=i)) in active for i in range(7)]


def _continue_learning(db: DbSession, session: PlayerSession) -> ContinueLearning | None:
    completed = list(
        db.scalars(
            select(LessonProgress).where(LessonProgress.session_id == session.id)
        )
    )
    done: dict[str, set[int]] = {}
    for row in completed:
        done.setdefault(row.cipher_slug, set()).add(row.step)
    for track in TRACKS:
        steps = done.get(track.slug, set())
        if len(steps) >= 5:
            continue
        next_step = next(s for s in range(1, 6) if s not in steps)
        lessons = _lessons_for(track.slug)
        return ContinueLearning(
            cipher_slug=track.slug,
            cipher_name=track.name,
            step=next_step,
            total_steps=5,
            title=lessons[next_step - 1],
        )
    return None


def _lessons_for(slug: str) -> list[str]:
    from app.content.curriculum import LESSONS

    return [lesson.title for lesson in LESSONS[slug]]


def _friend_signal(db: DbSession, session: PlayerSession) -> tuple[list[InvitationCard], list[FriendActivity]]:
    invites = list(
        db.scalars(
            select(DuelInvite)
            .where(
                DuelInvite.to_session_id == session.id,
                DuelInvite.status == DuelInviteStatus.PENDING,
            )
            .order_by(DuelInvite.created_at.desc())
            .limit(3)
        )
    )
    cards: list[InvitationCard] = []
    for invite in invites:
        sender = db.get(PlayerSession, invite.from_session_id)
        if sender is not None:
            cards.append(
                InvitationCard(id=invite.id, from_display_name=sender.display_name or "A friend")
            )

    # Friend activity: recent completions by accepted friends.
    from app.models import Friendship, FriendshipStatus

    rows = db.execute(
        select(PlayerSession, Progress)
        .join(Progress, Progress.session_id == PlayerSession.id)
        .join(Friendship, Friendship.status == FriendshipStatus.ACCEPTED)
        .where(
            (Friendship.requester_id == session.id) | (Friendship.addressee_id == session.id)
        )
        .where(Progress.completion_count > 0)
        .order_by(Progress.updated_at.desc())
        .limit(4)
    ).all()
    activity: list[FriendActivity] = []
    seen: set[int] = set()
    for friend, progress in rows:
        if friend.id in seen or friend.id == session.id:
            continue
        seen.add(friend.id)
        mission = db.get(Mission, progress.mission_id)
        activity.append(
            FriendActivity(
                display_name=friend.display_name or "A friend",
                action=f"completed {mission.title if mission else 'a mission'}",
                when=progress.updated_at,
            )
        )
    return cards, activity


@router.get("/home", response_model=HomeResponse)
def home(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> HomeResponse:
    profile = build_profile(db, session)
    xp = total_xp(db, session)
    level, _, ceiling = level_for_xp(xp)
    streak, _ = streak_from_days(activity_days(db, session))

    # Daily mission: the published mission this session has progressed least.
    daily = None
    mission = daily_mission(db)
    if mission is not None:
        progress = db.scalar(
            select(Progress).where(
                Progress.session_id == session.id, Progress.mission_id == mission.id
            )
        )
        daily = DailyMissionCard(
            slug=mission.slug,
            title=mission.title,
            difficulty=mission.difficulty.value
            if hasattr(mission.difficulty, "value")
            else str(mission.difficulty),
            cipher_name="Caesar",
            estimated_minutes=mission.estimated_minutes,
            completed=bool(progress and progress.completion_count > 0),
            best_score=progress.best_score if progress and progress.completion_count else None,
        )

    name = session.display_name or "player"
    greeting = f"Welcome back, {name}" if profile.missions_solved else "Welcome to CipherQuest"

    invitations, activity = _friend_signal(db, session)

    return HomeResponse(
        greeting=greeting,
        progress=ProgressStrip(
            level=level,
            xp=xp,
            level_ceiling=ceiling,
            streak_days=streak,
            missions_solved=profile.missions_solved,
        ),
        daily_mission=daily,
        week_dots=_week_dots(db, session),
        weekly_cup=build_cup(db, session),
        continue_learning=_continue_learning(db, session),
        invitations=invitations,
        friend_activity=activity,
        suggested_next=None,
    )


__all__ = ["router"]
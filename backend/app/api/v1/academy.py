"""Academy endpoints: tracks, lesson pages, completion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.content.curriculum import LESSONS, TRACKS, TRACK_BY_SLUG
from app.models import LessonProgress, PlayerSession
from app.schemas.lesson import (
    AcademyResponse,
    LessonCompleteResponse,
    LessonExample,
    LessonResponse,
    LessonSummary,
    TrackResponse,
    TrackSummary,
)
from app.services.profile import LESSON_XP, total_xp

router = APIRouter(prefix="/lessons", tags=["academy"])

XP_PER_LESSON = LESSON_XP


def _completed_steps(db: DbSession, session: PlayerSession) -> dict[str, set[int]]:
    rows = db.execute(
        select(LessonProgress.cipher_slug, LessonProgress.step).where(
            LessonProgress.session_id == session.id
        )
    ).all()
    done: dict[str, set[int]] = {}
    for slug, step in rows:
        done.setdefault(str(slug), set()).add(int(step))
    return done


@router.get("", response_model=AcademyResponse)
def academy(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AcademyResponse:
    done = _completed_steps(db, session)
    tracks: list[TrackSummary] = []
    suggested: str | None = None
    total_done = 0
    for track in TRACKS:
        completed = len(done.get(track.slug, set()))
        total_done += completed
        if completed >= 5:
            status = "complete"
            current = 5
        elif completed == 0:
            status = "not_started"
            current = 1
        else:
            status = "in_progress"
            current = next(s for s in range(1, 6) if s not in done[track.slug])
        if suggested is None and status != "complete":
            suggested = track.slug
        tracks.append(
            TrackSummary(
                slug=track.slug,
                name=track.name,
                blurb=track.blurb,
                difficulty=track.difficulty,
                lessons_total=5,
                lessons_completed=completed,
                current_step=current,
                status=status,
            )
        )
    return AcademyResponse(
        tracks=tracks,
        total_lessons_completed=total_done,
        total_lessons=len(TRACKS) * 5,
        suggested_next=suggested,  # type: ignore[arg-type]
    )


@router.get("/{slug}", response_model=TrackResponse)
def track_detail(
    slug: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> TrackResponse:
    track = TRACK_BY_SLUG.get(slug)
    if track is None:
        raise HTTPException(status_code=404, detail={"code": "track_not_found", "message": "Unknown cipher track."})
    done = _completed_steps(db, session).get(slug, set())
    lessons = [
        LessonSummary(
            step=lesson.step,
            title=lesson.title,
            summary=lesson.summary,
            completed=lesson.step in done,
        )
        for lesson in LESSONS[slug]
    ]
    current = next((s for s in range(1, 6) if s not in done), 5)
    return TrackResponse(
        slug=track.slug,
        name=track.name,
        blurb=track.blurb,
        difficulty=track.difficulty,
        lessons=lessons,
        current_step=current,
        xp_available=(5 - len(done)) * XP_PER_LESSON,
    )


@router.get("/{slug}/{step}", response_model=LessonResponse)
def lesson_detail(
    slug: str,
    step: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> LessonResponse:
    lesson = _resolve_lesson(slug, step)
    track = TRACK_BY_SLUG[slug]
    done = _completed_steps(db, session).get(slug, set())
    rows = db.execute(
        select(LessonProgress).where(
            LessonProgress.session_id == session.id,
            LessonProgress.cipher_slug == slug,
            LessonProgress.step == step,
        )
    ).scalars().first()
    example = LessonExample(**lesson.example) if lesson.example else None
    return LessonResponse(
        slug=slug,
        track_name=track.name,
        step=step,
        title=lesson.title,
        summary=lesson.summary,
        body=lesson.body,
        example=example,
        completed=step in done,
        xp_awarded=rows.xp_awarded if rows else 0,
        next_step=step + 1 if step < 5 else None,
        total_steps=5,
    )


@router.post("/{slug}/{step}/complete", response_model=LessonCompleteResponse)
def complete_lesson(
    slug: str,
    step: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> LessonCompleteResponse:
    _resolve_lesson(slug, step)
    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.session_id == session.id,
            LessonProgress.cipher_slug == slug,
            LessonProgress.step == step,
        )
    )
    granted = 0
    if existing is None:
        db.add(
            LessonProgress(
                session_id=session.id,
                cipher_slug=slug,
                step=step,
                xp_awarded=XP_PER_LESSON,
            )
        )
        granted = XP_PER_LESSON
        db.commit()
    done = _completed_steps(db, session)
    completed_count = int(
        db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.session_id == session.id
            )
        )
        or 0
    )
    next_step = step + 1 if step < 5 else None
    return LessonCompleteResponse(
        completed=True,
        xp_awarded=granted,
        total_xp=total_xp(db, session),
        lessons_completed=completed_count,
        next_step=next_step,
        finished_track=len(done.get(slug, set())) >= 5,
    )


def _resolve_lesson(slug: str, step: int):
    lessons = LESSONS.get(slug)
    if lessons is None:
        raise HTTPException(status_code=404, detail={"code": "track_not_found", "message": "Unknown cipher track."})
    if step < 1 or step > len(lessons):
        raise HTTPException(status_code=404, detail={"code": "lesson_not_found", "message": "No such lesson step."})
    return lessons[step - 1]


__all__ = ["router"]
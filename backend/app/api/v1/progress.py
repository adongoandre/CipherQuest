"""Progress read endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_session
from app.core.database import get_db
from app.models import PlayerSession, Progress, PublicationStatus, Mission
from app.schemas.mission import ProgressSummary
from app.schemas.engagement import ProgressResponse
from app.services.scoring import COMPREHENSION_BONUS

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressResponse, summary="Current session's progress")
def get_progress_summary(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ProgressResponse:
    rows = list(
        db.scalars(select(Progress).where(Progress.session_id == session.id)).all()
    )

    missions = (
        list(
            db.scalars(
                select(Mission)
                .where(Mission.status == PublicationStatus.PUBLISHED)
                .order_by(Mission.display_order.asc())
            ).all()
        )
    )
    by_mission = {row.mission_id: row for row in rows}

    completed = [r for r in rows if r.completed_at is not None]
    comprehension_count = sum(1 for r in rows if r.comprehension_awarded)
    base_total = sum(r.xp_awarded for r in rows)

    summary = ProgressSummary(
        missions_completed=len(completed),
        total_puzzles_solved=sum(r.completion_count for r in rows),
        total_score=base_total,
        xp=base_total,
        completed_slugs=[
            m.slug for m in missions
            if m.id in by_mission and by_mission[m.id].completed_at is not None
        ],
    )

    return ProgressResponse(
        progress=summary,
        missions=[
            {
                "slug": m.slug,
                "title": m.title,
                "difficulty": m.difficulty.value,
                "display_order": m.display_order,
                "completed": m.id in by_mission and by_mission[m.id].completed_at is not None,
                "best_score": by_mission[m.id].best_score if m.id in by_mission else 0,
                "completion_count": (
                    by_mission[m.id].completion_count if m.id in by_mission else 0
                ),
                "comprehension_awarded": (
                    by_mission[m.id].comprehension_awarded if m.id in by_mission else False
                ),
            }
            for m in missions
        ],
    )


__all__ = ["router", "COMPREHENSION_BONUS"]

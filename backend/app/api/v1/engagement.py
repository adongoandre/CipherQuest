"""Feedback survey and client-reported analytics events."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_session
from app.api.errors import not_found
from app.core.database import get_db
from app.models import Feedback, Mission, PlayerSession
from app.schemas.engagement import FeedbackRequest, FeedbackResponse
from app.services import analytics

router = APIRouter(tags=["engagement"])

# Events the browser is allowed to report. Stage events (riddle_submitted,
# hint_used, mission_completed, …) are recorded server-side only, so a client
# cannot fabricate engagement data.
CLIENT_EVENTS = frozenset({"landing_view", "next_mission_clicked"})


@router.post("/feedback", response_model=FeedbackResponse, summary="Submit the optional survey")
def submit_feedback(
    body: FeedbackRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> FeedbackResponse:
    mission = db.scalar(
        select(Mission).where(Mission.slug == body.mission_slug)
    )
    if mission is None:
        raise not_found("mission_not_found", f"No mission matches {body.mission_slug!r}.")

    if not any(
        [body.clarity_rating, body.learned, body.enjoyment_rating, body.would_return, body.comment]
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "empty_feedback",
                "message": "Answer at least one survey question before submitting.",
            },
        )

    db.add(
        Feedback(
            mission_id=mission.id,
            session_id=session.id,
            clarity_rating=body.clarity_rating,
            learned=body.learned,
            enjoyment_rating=body.enjoyment_rating,
            would_return=body.would_return,
            comment=body.comment,
        )
    )
    analytics.record(db, "feedback_submitted", session=session, mission=mission,
                     answered=sum(
                         1 for v in
                         [body.clarity_rating, body.learned, body.enjoyment_rating,
                          body.would_return]
                         if v is not None
                     ))
    db.commit()
    return FeedbackResponse(saved=True, message="Thank you — your feedback was recorded.")


class AnalyticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_name: str = Field(min_length=1, max_length=60)
    mission_slug: str | None = Field(default=None, max_length=80)


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recorded: bool


@router.post("/analytics", response_model=AnalyticsResponse, summary="Record a client event")
def record_client_event(
    body: AnalyticsRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AnalyticsResponse:
    if body.event_name not in CLIENT_EVENTS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail={
                "code": "event_not_client_reportable",
                "message": f"{body.event_name!r} is recorded by the server, not the client.",
            },
        )

    mission = None
    if body.mission_slug:
        mission = db.scalar(select(Mission).where(Mission.slug == body.mission_slug))

    analytics.record(db, body.event_name, session=session, mission=mission)
    db.commit()
    return AnalyticsResponse(recorded=True)


__all__ = ["router", "CLIENT_EVENTS"]

"""Mission loop routes.

Stage transitions are driven by explicit player actions and recorded
server-side, so the client cannot skip ahead::

    riddle-attempt  -> reveals the key          (stage KEY_REVEAL)
    advance         -> reveals the clue         (stage CONTEXT_CLUE)
    advance         -> reveals the ciphertext   (stage DECRYPT)
    decrypt-attempt -> validates + scores       (stage EXPLANATION)
    comprehension   -> awards the final 5 pts
    reveal          -> opts into the solution without scoring
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_session
from app.api.errors import api_error, not_found
from app.cipher import normalise_riddle_answer
from app.core.database import get_db
from app.models import (
    Attempt,
    AttemptOutcome,
    AttemptStage,
    Mission,
    PlayerSession,
    Progress,
)
from app.schemas.attempt import (
    ComprehensionRequest,
    ComprehensionResponse,
    DecryptRequest,
    DecryptResponse,
    HintResponse,
    RevealRequest,
    RevealResponse,
    RiddleRequest,
    RiddleResponse,
)
from app.schemas.mission import (
    MissionListResponse,
    MissionListItem,
    MissionStage,
    ScoreBreakdown,
    Solution,
)
from app.services import analytics, scoring
from app.services.missions import (
    active_telling,
    build_payload,
    current_stage,
    daily_mission,
    decrypt_attempts,
    earned_score,
    find_mission,
    get_progress,
    hints_used,
    published_missions,
    riddle_attempts,
    _key_reveal,
)

router = APIRouter(prefix="/missions", tags=["missions"])


# --- helpers --------------------------------------------------------------


def _require_mission(db: DbSession, ident: str) -> Mission:
    mission = find_mission(db, ident)
    if mission is None:
        raise not_found("mission_not_found", f"No published mission matches {ident!r}.")
    return mission


def _namespaced_key(mission: Mission, key: str | None) -> str | None:
    if not key:
        return None
    return f"{mission.id}:{key}"[:64]


def _find_prior_attempt(
    db: DbSession, session: PlayerSession, namespaced: str | None
) -> Attempt | None:
    if not namespaced:
        return None
    return db.scalar(
        select(Attempt).where(
            Attempt.session_id == session.id,
            Attempt.idempotency_key == namespaced,
        )
    )


def _snapshot(mission: Mission, db: DbSession, session: PlayerSession):
    progress = get_progress(db, mission, session)
    view = active_telling(mission, progress.story_index)
    stage = current_stage(db, mission, session)
    revealed = hints_used(db, mission, session)
    return build_payload(
        view,
        stage,
        hints_revealed=revealed,
        is_completed=progress.completed_at is not None,
        revealed_hints=list(view.hints[:revealed]),
        earned=earned_score(db, mission, session) if stage == MissionStage.EXPLANATION else None,
        comprehension_awarded=progress.comprehension_awarded,
        telling_number=view.index + 1,
    )


# --- reads ----------------------------------------------------------------


@router.get("", response_model=MissionListResponse)
def list_missions(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> MissionListResponse:
    missions = published_missions(db)
    daily = daily_mission(db)
    completed = {
        p.mission_id
        for p in db.scalars(
            select(Progress).where(Progress.session_id == session.id)
        ).all()
        if p.completed_at is not None
    }
    return MissionListResponse(
        missions=[
            MissionListItem(
                id=m.id,
                slug=m.slug,
                title=m.title,
                difficulty=m.difficulty.value,
                cipher_type=m.cipher_type.value,
                estimated_minutes=m.estimated_minutes,
                display_order=m.display_order,
                is_completed=m.id in completed,
            )
            for m in missions
        ],
        daily_slug=daily.slug if daily else (missions[0].slug if missions else ""),
    )


@router.get("/daily")
def get_daily(
    response: Response,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
):
    mission = daily_mission(db)
    if mission is None:
        raise not_found("no_missions", "No published missions are available yet.")
    _record_mission_start(db, mission, session)
    db.commit()
    return _snapshot(mission, db, session)


@router.get("/{ident}")
def get_mission(
    ident: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
):
    mission = _require_mission(db, ident)
    _record_mission_start(db, mission, session)
    db.commit()
    return _snapshot(mission, db, session)


def _record_mission_start(db: DbSession, mission: Mission, session: PlayerSession) -> None:
    """Emit ``mission_started`` exactly once per session per mission."""
    from app.models import AnalyticsEvent

    already = db.scalar(
        select(AnalyticsEvent.id)
        .where(
            AnalyticsEvent.event_name == "mission_started",
            AnalyticsEvent.session_id == session.id,
            AnalyticsEvent.mission_id == mission.id,
        )
        .limit(1)
    )
    if already is None:
        analytics.record(db, "mission_started", session=session, mission=mission,
                         difficulty=mission.difficulty.value)


@router.post("/{ident}/restart")
def restart_mission(
    ident: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
):
    """Start this mission over.

    A mission that was never finished restarts on the same telling. A mission
    that was already solved advances to its next telling, so a replay never
    repeats a story the player has read. Completed rewards (XP, best score,
    comprehension bonus) are remembered and never granted twice — only the
    run itself is fresh: stage, hints and stored attempt scores reset.
    """
    mission = _require_mission(db, ident)
    progress = get_progress(db, mission, session)

    if progress.completed_at is not None:
        progress.story_index = (progress.story_index + 1) % mission.telling_count

    db.execute(
        delete(Attempt).where(
            Attempt.session_id == session.id,
            Attempt.mission_id == mission.id,
        )
    )
    analytics.record(
        db,
        "mission_restarted",
        session=session,
        mission=mission,
        story_index=progress.story_index,
    )
    db.commit()
    return _snapshot(mission, db, session)


# --- riddle ---------------------------------------------------------------


@router.post("/{ident}/riddle-attempt", response_model=RiddleResponse)
def submit_riddle(
    ident: str,
    body: RiddleRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RiddleResponse:
    mission = _require_mission(db, ident)
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    namespaced = _namespaced_key(mission, body.idempotency_key)

    prior = _find_prior_attempt(db, session, namespaced)
    if prior is not None and prior.outcome == AttemptOutcome.CORRECT:
        db.commit()
        return RiddleResponse(
            correct=True,
            stage=current_stage(db, mission, session),
            attempts=riddle_attempts(db, mission, session),
            key_reveal=_key_reveal(view),
            message="Correct — this is the key for your mission.",
        )

    correct = normalise_riddle_answer(body.answer, view.accepted_riddle_answers)

    attempt = Attempt(
        session_id=session.id,
        mission_id=mission.id,
        stage=AttemptStage.KEY_REVEAL if correct else AttemptStage.RIDDLE,
        outcome=AttemptOutcome.CORRECT if correct else AttemptOutcome.INCORRECT,
        hints_used=hints_used(db, mission, session),
        score=0,
        idempotency_key=namespaced,
    )
    db.add(attempt)
    analytics.record(
        db,
        "riddle_submitted",
        session=session,
        mission=mission,
        outcome="correct" if correct else "incorrect",
    )
    if correct:
        analytics.record(db, "key_revealed", session=session, mission=mission,
                         key_rule=mission.key_rule_id, parameter=mission.parameter)
    db.commit()

    if correct:
        return RiddleResponse(
            correct=True,
            stage=MissionStage.KEY_REVEAL,
            attempts=riddle_attempts(db, mission, session),
            key_reveal=_key_reveal(view),
            message="Correct — this is the key for your mission.",
        )
    return RiddleResponse(
        correct=False,
        stage=MissionStage.RIDDLE,
        attempts=riddle_attempts(db, mission, session),
        key_reveal=None,
        message="Not quite. Re-read the riddle, or reveal a hint.",
    )


# --- progressive reveals --------------------------------------------------


class AdvanceResponse(BaseModel):
    stage: MissionStage
    contextual_clue: str | None = None
    ciphertext: str | None = None
    message: str

    model_config = {"extra": "forbid"}


@router.post("/{ident}/advance", response_model=AdvanceResponse)
def advance_stage(
    ident: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AdvanceResponse:
    mission = _require_mission(db, ident)
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    stage = current_stage(db, mission, session)

    if stage == MissionStage.KEY_REVEAL:
        db.add(
            Attempt(
                session_id=session.id,
                mission_id=mission.id,
                stage=AttemptStage.CONTEXT_CLUE,
                outcome=AttemptOutcome.CORRECT,
                hints_used=hints_used(db, mission, session),
            )
        )
        analytics.record(db, "context_clue_viewed", session=session, mission=mission)
        db.commit()
        return AdvanceResponse(
            stage=MissionStage.CONTEXT_CLUE,
            contextual_clue=view.contextual_clue,
            message="Read the clue, then reveal the message.",
        )

    if stage == MissionStage.CONTEXT_CLUE:
        db.add(
            Attempt(
                session_id=session.id,
                mission_id=mission.id,
                stage=AttemptStage.DECRYPT,
                outcome=AttemptOutcome.CORRECT,
                hints_used=hints_used(db, mission, session),
            )
        )
        db.commit()
        return AdvanceResponse(
            stage=MissionStage.DECRYPT,
            contextual_clue=view.contextual_clue,
            ciphertext=view.ciphertext,
            message="Decrypt the message and submit your answer.",
        )

    raise _conflict(
        "stage_not_advanceable",
        f"Nothing to reveal while the mission is at stage {stage.value!r}.",
    )


def _conflict(code: str, message: str):
    from fastapi import HTTPException

    return HTTPException(status_code=409, detail={"code": code, "message": message})


# --- hints ----------------------------------------------------------------


@router.post("/{ident}/hint", response_model=HintResponse)
def next_hint(
    ident: str,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> HintResponse:
    mission = _require_mission(db, ident)
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    used = hints_used(db, mission, session)
    total = len(view.hints)

    if used >= total:
        raise _conflict("no_hints_remaining", "All hints for this mission are used.")

    db.add(
        Attempt(
            session_id=session.id,
            mission_id=mission.id,
            stage=AttemptStage.HINT,
            outcome=AttemptOutcome.HINT_REQUESTED,
            hints_used=used + 1,
        )
    )
    analytics.record(db, "hint_used", session=session, mission=mission,
                     hint_number=used + 1)
    db.commit()

    return HintResponse(
        hint_number=used + 1,
        total_hints=total,
        hint=view.hints[used],
        hints_used=used + 1,
        score_penalty_note=(
            "Hints are free to use, but the 10-point no-hint bonus is lost "
            "from 100."
            if used == 0
            else "The 10-point no-hint bonus has already been lost."
        ),
    )


# --- decrypt --------------------------------------------------------------


@router.post("/{ident}/decrypt-attempt", response_model=DecryptResponse)
def submit_decrypt(
    ident: str,
    body: DecryptRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> DecryptResponse:
    mission = _require_mission(db, ident)
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    stage = current_stage(db, mission, session)

    if stage not in (MissionStage.DECRYPT, MissionStage.EXPLANATION):
        raise _conflict(
            "decrypt_locked",
            "Solve the riddle and read the clue before submitting a decryption.",
        )

    namespaced = _namespaced_key(mission, body.idempotency_key)
    prior = _find_prior_attempt(db, session, namespaced)

    if prior is not None:
        # Replay of a submission we already scored: return the stored outcome.
        db.commit()
        return _decrypt_response(
            mission,
            db,
            session,
            correct=prior.outcome == AttemptOutcome.CORRECT,
            stored_score=prior.score,
            progress_awarded=False,
        )

    from app.cipher import answers_match

    used = hints_used(db, mission, session)
    correct = answers_match(body.answer, view.plaintext_answer)

    cfg = mission.scoring_config or {}
    score = scoring.compute_score(
        correct=correct,
        hints_used=used,
        elapsed_seconds=body.elapsed_seconds,
        timed=bool(cfg.get("time_bonus_enabled", False)),
        target_seconds=mission.estimated_minutes * 60,
    )

    db.add(
        Attempt(
            session_id=session.id,
            mission_id=mission.id,
            stage=AttemptStage.EXPLANATION if correct else AttemptStage.DECRYPT,
            outcome=AttemptOutcome.CORRECT if correct else AttemptOutcome.INCORRECT,
            hints_used=used,
            elapsed_seconds=body.elapsed_seconds,
            score=score.total,
            idempotency_key=namespaced,
        )
    )
    analytics.record(
        db,
        "decrypt_submitted",
        session=session,
        mission=mission,
        outcome="correct" if correct else "incorrect",
        hints_used=used,
    )

    progress_awarded = False
    if correct:
        progress = get_progress(db, mission, session)
        if progress.completed_at is None:
            # First completion: grant the reward exactly once.
            progress.completed_at = datetime.now(timezone.utc)
            progress.completion_count = 1
            progress.xp_awarded = score.total
            progress.hints_used_best = used
            progress_awarded = True
        else:
            # Replays may improve the best score, but never re-grant XP.
            progress.completion_count += 1
            progress.hints_used_best = min(progress.hints_used_best, used)
        progress.best_score = max(progress.best_score, score.total)
        analytics.record(db, "mission_completed", session=session, mission=mission,
                         score=score.total, hints_used=used)
        db.commit()
    else:
        db.commit()

    return _decrypt_response(
        mission, db, session, correct=correct, stored_score=score.total,
        progress_awarded=progress_awarded,
    )


def _decrypt_response(
    mission: Mission,
    db: DbSession,
    session: PlayerSession,
    *,
    correct: bool,
    stored_score: int,
    progress_awarded: bool,
) -> DecryptResponse:
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    used = hints_used(db, mission, session)
    if correct:
        breakdown = ScoreBreakdown(
            total=stored_score,
            solve_points=scoring.SOLVE_POINTS if stored_score else 0,
            no_hint_bonus=scoring.NO_HINT_BONUS if used == 0 and stored_score else 0,
            time_bonus=max(0, stored_score - scoring.SOLVE_POINTS - (
                scoring.NO_HINT_BONUS if used == 0 else 0)),
            comprehension_bonus=0,
            hints_used=used,
            elapsed_seconds=None,
            breakdown={"correct": True, "total": stored_score},
        )
        return DecryptResponse(
            correct=True,
            stage=MissionStage.EXPLANATION,
            attempts=decrypt_attempts(db, mission, session),
            hints_used=used,
            score=breakdown,
            solution=Solution(
                plaintext=view.plaintext_answer,
                explanation=view.explanation,
                worked_example=view.worked_example,
            ),
            message="Correct — here is the message and how it was made.",
            progress_awarded=progress_awarded,
            comprehension_check=view.comprehension_check or None,
        )
    return DecryptResponse(
        correct=False,
        stage=current_stage(db, mission, session),
        attempts=decrypt_attempts(db, mission, session),
        hints_used=used,
        score=None,
        solution=None,
        message="Not quite. Check the shift direction and try again, or reveal a hint.",
        progress_awarded=False,
    )


# --- reveal + comprehension ----------------------------------------------


@router.post("/{ident}/reveal", response_model=RevealResponse)
def reveal_solution(
    ident: str,
    body: RevealRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> RevealResponse:
    mission = _require_mission(db, ident)
    view = active_telling(mission, get_progress(db, mission, session).story_index)
    db.add(
        Attempt(
            session_id=session.id,
            mission_id=mission.id,
            stage=AttemptStage.EXPLANATION,
            outcome=AttemptOutcome.REVEALED,
            hints_used=hints_used(db, mission, session),
            score=0,
        )
    )
    analytics.record(db, "solution_revealed", session=session, mission=mission,
                     reason=body.reason)
    db.commit()
    return RevealResponse(
        stage=MissionStage.EXPLANATION,
        solution=Solution(
            plaintext=view.plaintext_answer,
            explanation=view.explanation,
            worked_example=view.worked_example,
        ),
        score_awarded=0,
        message="Solution revealed. No solve points are awarded for a reveal.",
    )


@router.post("/{ident}/comprehension", response_model=ComprehensionResponse)
def submit_comprehension(
    ident: str,
    body: ComprehensionRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ComprehensionResponse:
    mission = _require_mission(db, ident)
    if current_stage(db, mission, session) != MissionStage.EXPLANATION:
        raise _conflict("explanation_required",
                        "Finish or reveal the mission before the comprehension check.")

    view = active_telling(mission, get_progress(db, mission, session).story_index)
    check = view.comprehension_check or {}
    correct_index = int(check.get("correct_index", -1))
    correct = body.choice == correct_index

    progress = get_progress(db, mission, session)
    awarded = False
    if correct and not progress.comprehension_awarded:
        progress.comprehension_awarded = True
        progress.xp_awarded += scoring.COMPREHENSION_BONUS
        awarded = True

    analytics.record(db, "comprehension_answered", session=session, mission=mission,
                     outcome="correct" if correct else "incorrect")
    db.commit()

    return ComprehensionResponse(
        correct=correct,
        earned=scoring.COMPREHENSION_BONUS if correct else 0,
        total=progress.xp_awarded,
        correct_index=correct_index,
        explanation=str(check.get("explanation", "")),
        awarded=awarded,
    )


__all__ = ["router", "api_error"]

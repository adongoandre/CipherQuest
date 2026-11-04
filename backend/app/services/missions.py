"""Mission state services: sessions, stages and stage-gated payloads.

The stage is *derived* from recorded attempts rather than trusted from the
client, so a player cannot skip the riddle, jump straight to the ciphertext or
request the explanation before earning it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    AttemptOutcome,
    AttemptStage,
    CipherType,
    Mission,
    PlayerSession,
    Progress,
    PublicationStatus,
    new_session_token,
)
from app.schemas.mission import (
    KeyReveal,
    MissionContextClue,
    MissionDecrypt,
    MissionExplanation,
    MissionStage,
    ScoreBreakdown,
    Solution,
)
from app.services.scoring import COMPREHENSION_BONUS, NO_HINT_BONUS, SOLVE_POINTS

CIPHER_NAMES: dict[str, str] = {
    CipherType.CAESAR.value: "Caesar Cipher",
    CipherType.ATBASH.value: "Atbash Cipher",
}

_STAGE_ORDER = [
    MissionStage.RIDDLE,
    MissionStage.KEY_REVEAL,
    MissionStage.CONTEXT_CLUE,
    MissionStage.DECRYPT,
    MissionStage.EXPLANATION,
]

# Every field a telling can override. The base columns of the mission row hold
# telling #1; Mission.stories holds tellings #2..#N with these same keys.
TELLING_FIELDS = frozenset(
    {
        "narrative",
        "riddle_prompt",
        "accepted_riddle_answers",
        "key_rule_id",
        "key_rule_description",
        "key_type",
        "parameter",
        "contextual_clue",
        "ciphertext",
        "plaintext_answer",
        "hints",
        "comprehension_check",
        "explanation",
        "worked_example",
    }
)


class Telling:
    """A mission viewed through one telling's content.

    Attributes resolve against the override story first and fall back to the
    mission row, so every existing payload builder keeps working unchanged
    while narrative, riddle, ciphertext and hints follow the active telling.
    """

    __slots__ = ("_mission", "_story", "index")

    def __init__(self, mission: Mission, story: dict | None = None, index: int = 0) -> None:
        self._mission = mission
        self._story = story
        self.index = index

    def __getattr__(self, name: str):
        # Only called for names the slots do not define, so no recursion risk.
        story = self._story
        if story and name in TELLING_FIELDS:
            return story[name]
        return getattr(self._mission, name)


def active_telling(mission: Mission, story_index: int = 0) -> Telling:
    """Resolve ``story_index`` against the mission's tellings (wrapping)."""
    stories = mission.stories or []
    total = 1 + len(stories)
    index = story_index % total if total else 0
    if index <= 0:
        return Telling(mission, index=0)
    return Telling(mission, stories[index - 1], index=index)


# --- sessions -------------------------------------------------------------


def resolve_session(db: Session, token: str | None) -> tuple[PlayerSession, bool]:
    """Return an existing session for ``token`` or create a fresh one.

    Returns ``(session, created)``. An unknown or blank token always yields a
    brand-new pseudonymous session — never someone else's.
    """
    if token:
        token = token.strip()
        if len(token) <= 64:
            existing = db.scalar(select(PlayerSession).where(PlayerSession.token == token))
            if existing is not None:
                existing.last_seen_at = datetime.now(timezone.utc)
                return existing, False

    session = PlayerSession(token=new_session_token())
    db.add(session)
    db.flush()
    return session, True


# --- stage derivation -----------------------------------------------------


def hints_used(db: Session, mission: Mission, session: PlayerSession) -> int:
    stmt = select(func.count(Attempt.id)).where(
        Attempt.mission_id == mission.id,
        Attempt.session_id == session.id,
        Attempt.outcome == AttemptOutcome.HINT_REQUESTED,
    )
    return int(db.scalar(stmt) or 0)


def hint_attempts(db: Session, mission: Mission, session: PlayerSession) -> int:
    return hints_used(db, mission, session)


def riddle_attempts(db: Session, mission: Mission, session: PlayerSession) -> int:
    stmt = select(func.count(Attempt.id)).where(
        Attempt.mission_id == mission.id,
        Attempt.session_id == session.id,
        Attempt.stage == AttemptStage.RIDDLE,
        Attempt.outcome.in_([AttemptOutcome.CORRECT, AttemptOutcome.INCORRECT]),
    )
    return int(db.scalar(stmt) or 0)


def decrypt_attempts(db: Session, mission: Mission, session: PlayerSession) -> int:
    stmt = select(func.count(Attempt.id)).where(
        Attempt.mission_id == mission.id,
        Attempt.session_id == session.id,
        Attempt.stage.in_([AttemptStage.DECRYPT, AttemptStage.EXPLANATION]),
        Attempt.outcome.in_([AttemptOutcome.CORRECT, AttemptOutcome.INCORRECT]),
    )
    return int(db.scalar(stmt) or 0)


def _reached_stages(db: Session, mission: Mission, session: PlayerSession) -> set[AttemptStage]:
    stmt = select(Attempt.stage).where(
        Attempt.mission_id == mission.id, Attempt.session_id == session.id
    )
    return set(db.scalars(stmt).all())


def current_stage(db: Session, mission: Mission, session: PlayerSession) -> MissionStage:
    """Return the furthest stage whose content this session has actually received.

    Attempts record *delivery* of each reveal, so the highest rung reached on
    the ladder below is exactly what the player has seen. ``HINT`` attempts are
    deliberately absent from the ladder and never advance the stage.
    """
    reached = _reached_stages(db, mission, session)
    stage = MissionStage.RIDDLE
    for rung in _STAGE_ORDER:
        if rung.value in {s.value for s in reached}:
            stage = rung
    return stage


def get_progress(db: Session, mission: Mission, session: PlayerSession) -> Progress:
    """Fetch or create the progress row for this (session, mission) pair."""
    row = db.scalar(
        select(Progress).where(
            Progress.session_id == session.id, Progress.mission_id == mission.id
        )
    )
    if row is None:
        row = Progress(session_id=session.id, mission_id=mission.id)
        db.add(row)
        db.flush()
    return row


def find_mission(db: Session, ident: str | int) -> Mission | None:
    stmt = select(Mission).where(Mission.status == PublicationStatus.PUBLISHED)
    if isinstance(ident, int) or (isinstance(ident, str) and ident.isdigit()):
        stmt = stmt.where(Mission.id == int(ident))
    else:
        stmt = stmt.where(Mission.slug == str(ident))
    return db.scalar(stmt)


def published_missions(db: Session) -> list[Mission]:
    stmt = (
        select(Mission)
        .where(Mission.status == PublicationStatus.PUBLISHED)
        .order_by(Mission.display_order.asc(), Mission.id.asc())
    )
    return list(db.scalars(stmt))


def daily_mission(db: Session, today: datetime | None = None) -> Mission | None:
    """Deterministic mission-of-the-day, rotating by ordinal day."""
    missions = published_missions(db)
    if not missions:
        return None
    day = (today or datetime.now(timezone.utc)).toordinal()
    return missions[day % len(missions)]


# --- stage-gated payloads -------------------------------------------------


def _brief(
    mission,
    stage: MissionStage,
    hints_revealed: int,
    is_completed: bool,
    telling_number: int = 1,
) -> dict:
    return {
        "id": mission.id,
        "slug": mission.slug,
        "title": mission.title,
        "narrative": mission.narrative,
        "difficulty": mission.difficulty.value,
        "cipher_type": mission.cipher_type.value,
        "cipher_name": CIPHER_NAMES.get(mission.cipher_type.value, mission.cipher_type.value),
        "estimated_minutes": mission.estimated_minutes,
        "stage": stage,
        "hint_count_total": len(mission.hints),
        "hints_revealed": hints_revealed,
        "is_completed": is_completed,
        "telling_number": telling_number,
        "telling_count": mission.telling_count,
    }


def _key_reveal(mission) -> KeyReveal:
    return KeyReveal(
        accepted_answer=mission.accepted_riddle_answers[0].upper(),
        key_type=mission.key_type,
        parameter=mission.parameter,
        key_rule_description=mission.key_rule_description,
    )


def earned_score(db: Session, mission: Mission, session: PlayerSession) -> ScoreBreakdown | None:
    """Rebuild the score this session earned, or ``None`` for a revealed solution.

    Only a *correct* decrypt attempt counts; a reveal records no points and must
    keep presenting as a reveal after a page reload.
    """
    from app.services import scoring

    row = db.scalar(
        select(Attempt)
        .where(
            Attempt.mission_id == mission.id,
            Attempt.session_id == session.id,
            Attempt.stage == AttemptStage.EXPLANATION,
            Attempt.outcome == AttemptOutcome.CORRECT,
        )
        .order_by(Attempt.id.desc())
        .limit(1)
    )
    if row is None or not row.score:
        return None

    solve = scoring.SOLVE_POINTS
    no_hint = scoring.NO_HINT_BONUS if row.hints_used == 0 else 0
    time_bonus = max(0, row.score - solve - no_hint)
    return ScoreBreakdown(
        total=row.score,
        solve_points=solve,
        no_hint_bonus=no_hint,
        time_bonus=time_bonus,
        comprehension_bonus=0,
        hints_used=row.hints_used,
        elapsed_seconds=row.elapsed_seconds,
        breakdown={"correct": True, "total": row.score},
    )


def build_payload(
    mission,
    stage: MissionStage,
    *,
    hints_revealed: int,
    is_completed: bool,
    revealed_hints: list[str] | None = None,
    riddle_prompt: bool = True,
    earned: ScoreBreakdown | None = None,
    comprehension_awarded: bool = False,
    telling_number: int = 1,
):
    """Return the narrowest response model that satisfies ``stage``.

    ``mission`` may be a :class:`Mission` or a :class:`Telling` view of one.
    """
    base = _brief(mission, stage, hints_revealed, is_completed, telling_number)
    shown = list(revealed_hints or [])[:hints_revealed]

    if stage == MissionStage.RIDDLE:
        return _riddle(mission, base)

    if stage == MissionStage.KEY_REVEAL:
        from app.schemas.mission import MissionKeyReveal

        return MissionKeyReveal(**base, key_reveal=_key_reveal(mission))

    if stage == MissionStage.CONTEXT_CLUE:
        return MissionContextClue(**base, key_reveal=_key_reveal(mission),
                                  contextual_clue=mission.contextual_clue)

    if stage == MissionStage.DECRYPT:
        return MissionDecrypt(
            **base,
            key_reveal=_key_reveal(mission),
            contextual_clue=mission.contextual_clue,
            ciphertext=mission.ciphertext,
            revealed_hints=shown,
        )

    if stage == MissionStage.EXPLANATION:
        return MissionExplanation(
            **base,
            key_reveal=_key_reveal(mission),
            contextual_clue=mission.contextual_clue,
            ciphertext=mission.ciphertext,
            revealed_hints=shown,
            solution=Solution(
                plaintext=mission.plaintext_answer,
                explanation=mission.explanation,
                worked_example=mission.worked_example,
            ),
            comprehension_check=mission.comprehension_check or None,
            earned_score=earned,
            comprehension_awarded=comprehension_awarded,
        )

    # Defensive default: riddle stage.
    return _riddle(mission, base)


def _riddle(mission: Mission, base: dict):
    from app.schemas.mission import MissionRiddle

    return MissionRiddle(**base, riddle_prompt=mission.riddle_prompt)


SCORE_POINTS = {
    "solve": SOLVE_POINTS,
    "no_hint": NO_HINT_BONUS,
    "comprehension": COMPREHENSION_BONUS,
}

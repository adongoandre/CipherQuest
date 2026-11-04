"""Admin mission editor: author, verify, publish, retire, audit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.cipher import encrypt, decrypt
from app.models import (
    AuditLog,
    CipherType,
    Difficulty,
    Mission,
    PlayerSession,
    PublicationStatus,
)
from app.schemas.admin import (
    AdminMissionDetail,
    AdminMissionSummary,
    AuditEntry,
    AuditListResponse,
    MissionDraftRequest,
    PublishResult,
    VerifyResult,
)
from app.services.accounts import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def _verify(plaintext: str, ciphertext: str, shift: int) -> VerifyResult:
    problems: list[str] = []
    expected = encrypt(plaintext, shift)
    if expected != ciphertext:
        problems.append("Ciphertext does not match encrypt(plaintext, shift).")
    round_trip = decrypt(ciphertext, shift) == plaintext
    if not round_trip:
        problems.append("Ciphertext does not decrypt back to the stored plaintext.")
    return VerifyResult(
        verified=not problems,
        problems=problems,
        round_trip_ok=round_trip,
        parameter=shift,
        ciphertext=ciphertext,
        plaintext=plaintext,
    )


def _detail(db: DbSession, mission: Mission) -> AdminMissionDetail:
    shift = int(mission.parameter or 0)
    verification = _verify(mission.plaintext_answer, mission.ciphertext or "", shift)
    return AdminMissionDetail(
        id=mission.id,
        slug=mission.slug,
        title=mission.title,
        status=mission.status.value,
        difficulty=mission.difficulty.value,
        cipher_type=mission.cipher_type.value,
        estimated_minutes=mission.estimated_minutes,
        narrative=mission.narrative,
        riddle_prompt=mission.riddle_prompt,
        accepted_riddle_answers=list(mission.accepted_riddle_answers or []),
        key_rule_description=mission.key_rule_description or "",
        contextual_clue=mission.contextual_clue,
        plaintext_answer=mission.plaintext_answer,
        hints=list(mission.hints or []),
        parameter=shift,
        ciphertext=mission.ciphertext,
        verification=verification,
        updated_at=mission.updated_at if hasattr(mission, "updated_at") else None,
    )


def _audit(db: DbSession, session: PlayerSession, action: str, entity_id: str, detail: dict) -> None:
    db.add(
        AuditLog(
            session_id=session.id,
            action=action,
            entity_type="mission",
            entity_id=entity_id,
            detail=detail,
        )
    )


@router.get("/missions", response_model=list[AdminMissionSummary])
def list_missions(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> list[AdminMissionSummary]:
    require_admin(session)
    rows = list(db.scalars(select(Mission).order_by(Mission.updated_at.desc())))
    out: list[AdminMissionSummary] = []
    for mission in rows:
        shift = int(mission.parameter or 0)
        verification = _verify(mission.plaintext_answer, mission.ciphertext or "", shift)
        out.append(
            AdminMissionSummary(
                id=mission.id,
                slug=mission.slug,
                title=mission.title,
                status=mission.status.value,
                difficulty=mission.difficulty.value,
                cipher_type=mission.cipher_type.value,
                verified=verification.verified,
                verify_problems=verification.problems,
            )
        )
    return out


@router.post("/missions", response_model=AdminMissionDetail)
def create_mission(
    payload: MissionDraftRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AdminMissionDetail:
    require_admin(session)
    shift = _shift_from_answer(payload.accepted_riddle_answers[0])
    ciphertext = encrypt(payload.plaintext_answer, shift)
    slug = _slugify(payload.title)
    if db.scalar(select(Mission).where(Mission.slug == slug)):
        raise HTTPException(
            status_code=409,
            detail={"code": "slug_exists", "message": "A mission with that title already exists."},
        )
    first_answer = payload.accepted_riddle_answers[0]
    explanation = (
        f"Your riddle answer \"{first_answer}\" has {shift} letters, so the key rule "
        f"\"{payload.key_rule_description}\" gives a Caesar shift of {shift}. "
        f"Shifting each letter of the plaintext by {shift} produces the ciphertext."
    )
    from app.content.missions import build_worked_example

    mission = Mission(
        slug=slug,
        title=payload.title,
        narrative=payload.narrative,
        riddle_prompt=payload.riddle_prompt,
        accepted_riddle_answers=payload.accepted_riddle_answers,
        key_rule_description=payload.key_rule_description,
        contextual_clue=payload.contextual_clue,
        plaintext_answer=payload.plaintext_answer,
        ciphertext=ciphertext,
        parameter=shift,
        hints=payload.hints,
        difficulty=Difficulty(payload.difficulty),
        cipher_type=CipherType(payload.cipher_type),
        estimated_minutes=payload.estimated_minutes,
        comprehension_check={},
        explanation=explanation,
        worked_example=build_worked_example(payload.plaintext_answer, shift),
        status=PublicationStatus.DRAFT,
    )
    db.add(mission)
    db.flush()
    _audit(db, session, "create", slug, {"title": payload.title, "parameter": shift})
    db.commit()
    db.refresh(mission)
    return _detail(db, mission)


@router.post("/missions/{mission_id}", response_model=AdminMissionDetail)
def update_mission(
    mission_id: int,
    payload: MissionDraftRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AdminMissionDetail:
    """Save a draft edit of an existing mission (rebuilds ciphertext and verification)."""
    require_admin(session)
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found", "message": "No such mission."})
    shift = _shift_from_answer(payload.accepted_riddle_answers[0])
    ciphertext = encrypt(payload.plaintext_answer, shift)
    slug = _slugify(payload.title)
    clash = db.scalar(select(Mission).where(Mission.slug == slug, Mission.id != mission_id))
    if clash:
        raise HTTPException(
            status_code=409,
            detail={"code": "slug_exists", "message": "A mission with that title already exists."},
        )
    first_answer = payload.accepted_riddle_answers[0]
    explanation = (
        f"Your riddle answer \"{first_answer}\" has {shift} letters, so the key rule "
        f"\"{payload.key_rule_description}\" gives a Caesar shift of {shift}. "
        f"Shifting each letter of the plaintext by {shift} produces the ciphertext."
    )
    from app.content.missions import build_worked_example

    mission.slug = slug
    mission.title = payload.title
    mission.narrative = payload.narrative
    mission.riddle_prompt = payload.riddle_prompt
    mission.accepted_riddle_answers = payload.accepted_riddle_answers
    mission.key_rule_description = payload.key_rule_description
    mission.contextual_clue = payload.contextual_clue
    mission.plaintext_answer = payload.plaintext_answer
    mission.ciphertext = ciphertext
    mission.parameter = shift
    mission.hints = payload.hints
    mission.difficulty = Difficulty(payload.difficulty)
    mission.cipher_type = CipherType(payload.cipher_type)
    mission.estimated_minutes = payload.estimated_minutes
    mission.explanation = explanation
    mission.worked_example = build_worked_example(payload.plaintext_answer, shift)
    db.add(mission)
    _audit(db, session, "update", slug, {"title": payload.title, "parameter": shift})
    db.commit()
    db.refresh(mission)
    return _detail(db, mission)


@router.get("/missions/{mission_id}", response_model=AdminMissionDetail)
def get_mission(
    mission_id: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AdminMissionDetail:
    require_admin(session)
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found", "message": "No such mission."})
    return _detail(db, mission)


@router.post("/missions/{mission_id}/verify", response_model=VerifyResult)
def verify_mission(
    mission_id: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> VerifyResult:
    require_admin(session)
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found", "message": "No such mission."})
    return _verify(mission.plaintext_answer, mission.ciphertext or "", int(mission.parameter or 0))


@router.post("/missions/{mission_id}/publish", response_model=PublishResult)
def publish_mission(
    mission_id: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> PublishResult:
    require_admin(session)
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found", "message": "No such mission."})
    verification = _verify(mission.plaintext_answer, mission.ciphertext or "", int(mission.parameter or 0))
    if not verification.verified:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "verification_failed",
                "message": "Round-trip verification failed; fix the mission before publishing.",
                "details": {"problems": verification.problems},
            },
        )
    mission.status = PublicationStatus.PUBLISHED
    db.add(mission)
    _audit(db, session, "publish", mission.slug, {"title": mission.title})
    db.commit()
    return PublishResult(id=mission.id, status="published", message=f'"{mission.title}" is now live.')


@router.post("/missions/{mission_id}/retire", response_model=PublishResult)
def retire_mission(
    mission_id: int,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> PublishResult:
    require_admin(session)
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail={"code": "mission_not_found", "message": "No such mission."})
    mission.status = PublicationStatus.RETIRED
    db.add(mission)
    _audit(db, session, "retire", mission.slug, {"title": mission.title})
    db.commit()
    return PublishResult(id=mission.id, status="retired", message=f'"{mission.title}" retired.')


@router.get("/audit", response_model=AuditListResponse)
def audit_log(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> AuditListResponse:
    require_admin(session)
    rows = list(
        db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50))
    )
    return AuditListResponse(
        entries=[
            AuditEntry(
                id=row.id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                detail=row.detail or {},
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


def _shift_from_answer(answer: str) -> int:
    from app.content.key_rules import apply_key_rule

    try:
        return int(apply_key_rule("letter_count", answer))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_key_rule", "message": f"Cannot derive a shift: {exc}"},
        ) from exc


def _slugify(title: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:80] or "mission"


__all__ = ["router"]
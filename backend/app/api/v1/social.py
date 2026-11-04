"""Social endpoints: friends, duel invitations, blocks and reports."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_db, get_session
from app.models import (
    Block,
    DuelInvite,
    DuelInviteStatus,
    Friendship,
    FriendshipStatus,
    LessonProgress,
    PlayerSession,
    Progress,
    Report,
)
from app.schemas.social import (
    ActionResult,
    BlockedEntry,
    BlockRequest,
    FriendEntry,
    FriendRequest,
    FriendRequestEntry,
    FriendRespondRequest,
    FriendsResponse,
    InvitationEntry,
    InviteRequest,
    RespondRequest,
)
from app.services.profile import level_for_xp, total_xp

router = APIRouter(tags=["social"])


def _level_of(db: DbSession, session: PlayerSession) -> int:
    return level_for_xp(total_xp(db, session))[0]


def _blocked_ids(db: DbSession, viewer_id: int) -> set[int]:
    rows = db.execute(
        select(Block.blocker_id, Block.blocked_id).where(
            or_(Block.blocker_id == viewer_id, Block.blocked_id == viewer_id)
        )
    ).all()
    ids: set[int] = set()
    for a, b in rows:
        ids.add(b if a == viewer_id else a)
    return ids


def _name_or_none(db: DbSession, display_name: str) -> PlayerSession | None:
    return db.scalar(
        select(PlayerSession).where(PlayerSession.display_name.ilike(display_name.strip()))
    )


def _resolve_target(db: DbSession, viewer: PlayerSession, display_name: str) -> PlayerSession:
    from fastapi import HTTPException

    target = _name_or_none(db, display_name)
    if target is None or target.id == viewer.id or target.id in _blocked_ids(db, viewer.id):
        raise HTTPException(
            status_code=404,
            detail={"code": "player_not_found", "message": "No player with that display name."},
        )
    return target


@router.get("/friends", response_model=FriendsResponse)
def friends(
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> FriendsResponse:
    blocked = _blocked_ids(db, session.id)
    rows = db.execute(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.ACCEPTED,
            or_(
                Friendship.requester_id == session.id,
                Friendship.addressee_id == session.id,
            ),
        )
    ).scalars()
    friend_entries: list[FriendEntry] = []
    for link in rows:
        other_id = link.addressee_id if link.requester_id == session.id else link.requester_id
        if other_id in blocked:
            continue
        other = db.get(PlayerSession, other_id)
        if other is None:
            continue
        friend_entries.append(
            FriendEntry(
                id=other.id,
                display_name=other.display_name or "Guest",
                level=_level_of(db, other),
            )
        )

    invites = list(
        db.scalars(
            select(DuelInvite)
            .where(
                DuelInvite.to_session_id == session.id,
                DuelInvite.status == DuelInviteStatus.PENDING,
            )
            .order_by(DuelInvite.created_at.desc())
        )
    )
    invitation_entries = []
    for invite in invites:
        sender = db.get(PlayerSession, invite.from_session_id)
        if sender is None or sender.id in blocked:
            continue
        invitation_entries.append(
            InvitationEntry(
                id=invite.id,
                from_display_name=sender.display_name or "A friend",
                created_at=invite.created_at,
            )
        )

    outgoing_rows = list(
        db.scalars(
            select(DuelInvite).where(
                DuelInvite.from_session_id == session.id,
                DuelInvite.status == DuelInviteStatus.PENDING,
            )
        )
    )
    outgoing = []
    for invite in outgoing_rows:
        target = db.get(PlayerSession, invite.to_session_id)
        if target is None:
            continue
        outgoing.append(
            InvitationEntry(
                id=invite.id,
                from_display_name=target.display_name or "A friend",
                created_at=invite.created_at,
            )
        )

    blocked_rows = list(
        db.scalars(select(Block).where(Block.blocker_id == session.id))
    )
    blocked_entries = []
    for block in blocked_rows:
        other = db.get(PlayerSession, block.blocked_id)
        if other is not None:
            blocked_entries.append(
                BlockedEntry(id=other.id, display_name=other.display_name or "A player")
            )

    # Pending friend requests: those waiting on me, and those I have sent.
    incoming_rows = list(
        db.scalars(
            select(Friendship)
            .where(
                Friendship.status == FriendshipStatus.PENDING,
                Friendship.addressee_id == session.id,
            )
            .order_by(Friendship.created_at.desc())
        )
    )
    sent_rows = list(
        db.scalars(
            select(Friendship)
            .where(
                Friendship.status == FriendshipStatus.PENDING,
                Friendship.requester_id == session.id,
            )
            .order_by(Friendship.created_at.desc())
        )
    )

    def _request_entry(link: Friendship) -> FriendRequestEntry | None:
        other_id = (
            link.requester_id if link.addressee_id == session.id else link.addressee_id
        )
        if other_id in blocked:
            return None
        other = db.get(PlayerSession, other_id)
        if other is None:
            return None
        return FriendRequestEntry(
            id=link.id,
            display_name=other.display_name or "Guest",
            level=_level_of(db, other),
            created_at=link.created_at,
        )

    requests_incoming: list[FriendRequestEntry] = []
    for link in incoming_rows:
        entry = _request_entry(link)
        if entry is not None:
            requests_incoming.append(entry)
    requests_outgoing: list[FriendRequestEntry] = []
    for link in sent_rows:
        entry = _request_entry(link)
        if entry is not None:
            requests_outgoing.append(entry)

    return FriendsResponse(
        friends=friend_entries,
        invitations=invitation_entries,
        pending_outgoing=outgoing,
        blocked=blocked_entries,
        requests_incoming=requests_incoming,
        requests_outgoing=requests_outgoing,
    )


@router.post("/friends/request", response_model=ActionResult)
def friend_request(
    payload: FriendRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    target = _resolve_target(db, session, payload.display_name)
    existing = db.scalar(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == session.id) & (Friendship.addressee_id == target.id),
                (Friendship.requester_id == target.id) & (Friendship.addressee_id == session.id),
            )
        )
    )
    if existing is not None:
        if existing.status == FriendshipStatus.ACCEPTED:
            return ActionResult(ok=True, message="You are already friends.")
        if existing.requester_id == session.id:
            return ActionResult(ok=True, message="A friend request is already pending.")
        existing.status = FriendshipStatus.ACCEPTED
        db.commit()
        return ActionResult(ok=True, message=f"You are now friends with {target.display_name}.")
    db.add(
        Friendship(
            requester_id=session.id, addressee_id=target.id,
            status=FriendshipStatus.PENDING,
        )
    )
    db.commit()
    return ActionResult(ok=True, message=f"Friend request sent to {target.display_name}.")


@router.post("/friends/respond", response_model=ActionResult)
def friend_respond(
    payload: FriendRespondRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    link = db.get(Friendship, payload.friendship_id)
    if link is None or link.addressee_id != session.id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={"code": "request_not_found", "message": "That friend request was not found."},
        )
    if payload.action == "accept":
        link.status = FriendshipStatus.ACCEPTED
        db.commit()
        return ActionResult(ok=True, message="Friend request accepted.")
    db.delete(link)
    db.commit()
    return ActionResult(ok=True, message="Friend request declined.")


@router.post("/invites", response_model=ActionResult)
def send_invite(
    payload: InviteRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    target = _resolve_target(db, session, payload.display_name)
    existing = db.scalar(
        select(DuelInvite).where(
            DuelInvite.from_session_id == session.id,
            DuelInvite.to_session_id == target.id,
            DuelInvite.status == DuelInviteStatus.PENDING,
        )
    )
    if existing is None:
        db.add(
            DuelInvite(
                from_session_id=session.id,
                to_session_id=target.id,
                status=DuelInviteStatus.PENDING,
            )
        )
        db.commit()
    return ActionResult(ok=True, message=f"Cipher Duel invitation sent to {target.display_name}.")


@router.post("/invites/respond", response_model=ActionResult)
def respond_invite(
    payload: RespondRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    invite = db.get(DuelInvite, payload.invite_id)
    if invite is None or invite.to_session_id != session.id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={"code": "invite_not_found", "message": "That invitation was not found."},
        )
    if invite.status != DuelInviteStatus.PENDING:
        return ActionResult(ok=True, message="That invitation was already handled.")
    if payload.action == "accept":
        invite.status = DuelInviteStatus.ACCEPTED
        db.commit()
        return ActionResult(ok=True, message="Invitation accepted. Opening the duel lobby.")
    invite.status = DuelInviteStatus.DECLINED
    db.commit()
    return ActionResult(ok=True, message="Invitation declined.")


@router.post("/blocks", response_model=ActionResult)
def block_player(
    payload: BlockRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    target = _name_or_none(db, payload.display_name)
    if target is None or target.id == session.id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail={"code": "player_not_found", "message": "No player with that display name."},
        )
    existing = db.scalar(
        select(Block).where(Block.blocker_id == session.id, Block.blocked_id == target.id)
    )
    if existing is None:
        db.add(Block(blocker_id=session.id, blocked_id=target.id))
        db.commit()
    return ActionResult(ok=True, message=f"{target.display_name} has been blocked.")


@router.post("/reports", response_model=ActionResult)
def report_player(
    payload: ReportRequest,
    db: DbSession = Depends(get_db),
    session: PlayerSession = Depends(get_session),
) -> ActionResult:
    target = _resolve_target(db, session, payload.display_name)
    db.add(Report(reporter_id=session.id, reported_id=target.id, reason=payload.reason))
    db.commit()
    return ActionResult(ok=True, message="Report submitted. Thank you for keeping the community safe.")


__all__ = ["router"]
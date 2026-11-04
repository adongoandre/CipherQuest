"""Account registration, login and admin resolution.

Passwords are hashed with PBKDF2-HMAC-SHA256 from the standard library — no
third-party dependency, constant-time comparison, per-password random salt.
The stored format is ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.

A session upgrades in place when it registers (all progress is kept). Login
resolves the account's own session and hands back its token, so a player can
sign in on a new device.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models import PlayerSession

HASH_SCHEME = "pbkdf2_sha256"
ITERATIONS = 600_000
_MIN_PASSWORD = 8


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    if len(password) < _MIN_PASSWORD:
        raise ValueError(f"password must be at least {_MIN_PASSWORD} characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{HASH_SCHEME}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, raw_iterations, salt_hex, digest_hex = stored.split("$")
        iterations = int(raw_iterations)
    except (ValueError, AttributeError):
        return False
    if scheme != HASH_SCHEME or iterations <= 0:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_admin_email(email: str | None) -> bool:
    """Admins are configured via the ADMIN_EMAILS env var (comma separated)."""
    if not email:
        return False
    raw = os.getenv("ADMIN_EMAILS", "")
    allowed = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return normalize_email(email) in allowed


def _display_name_taken(db: DbSession, display_name: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(PlayerSession.id).where(func.lower(PlayerSession.display_name) == display_name.lower())
    if exclude_id is not None:
        stmt = stmt.where(PlayerSession.id != exclude_id)
    return db.scalar(stmt) is not None


def unique_display_name(db: DbSession, display_name: str, *, exclude_id: int | None = None) -> str:
    """Reject duplicates outright; names must be unique to be addressable."""
    if _display_name_taken(db, display_name, exclude_id=exclude_id):
        raise HTTPException(
            status_code=409,
            detail={"code": "display_name_taken", "message": "That display name is already in use."},
        )
    return display_name


def register_account(
    db: DbSession,
    session: PlayerSession,
    *,
    display_name: str,
    email: str,
    password: str,
    accepted_terms: bool,
) -> PlayerSession:
    """Upgrade ``session`` in place into a full account."""
    if not accepted_terms:
        raise HTTPException(
            status_code=400,
            detail={"code": "terms_not_accepted", "message": "You must accept the terms to create an account."},
        )
    email = normalize_email(email)
    existing = db.scalar(select(PlayerSession).where(PlayerSession.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "email_taken", "message": "An account already exists for that email."},
        )
    unique_display_name(db, display_name, exclude_id=session.id)
    try:
        digest = hash_password(password)
    except ValueError as exc:  # pragma: no cover - schema catches this first
        raise HTTPException(status_code=400, detail={"code": "weak_password", "message": str(exc)}) from exc

    session.display_name = display_name
    session.email = email
    session.password_hash = digest
    session.is_admin = is_admin_email(email)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def authenticate(db: DbSession, *, email: str, password: str) -> PlayerSession:
    """Verify credentials and return the account's session."""
    account = db.scalar(select(PlayerSession).where(PlayerSession.email == normalize_email(email)))
    if account is None or not account.password_hash or not verify_password(password, account.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "message": "Email or password is incorrect."},
        )
    return account


def require_admin(session: PlayerSession) -> PlayerSession:
    if not session.is_admin:
        raise HTTPException(
            status_code=403,
            detail={"code": "admin_required", "message": "Administrator access is required."},
        )
    return session


__all__ = [
    "authenticate",
    "hash_password",
    "is_admin_email",
    "normalize_email",
    "register_account",
    "require_admin",
    "unique_display_name",
    "verify_password",
]
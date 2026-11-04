"""SQLAlchemy 2.x engine, session factory and declarative base."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all CipherQuest ORM models."""


def _sqlite_path(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    raw = database_url[len(prefix) :]
    if raw.startswith("/") and len(raw) > 1 and raw[1] == "/":
        # sqlite:////absolute/path
        return Path(raw[1:])
    if raw in {"", ":memory:"}:
        return None
    return Path(raw)


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create an engine, ensuring the SQLite parent directory exists."""
    url = database_url or get_settings().database_url
    sqlite_path = _sqlite_path(url)
    if sqlite_path is not None and str(sqlite_path) != ":memory:":
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:  # pragma: no cover
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

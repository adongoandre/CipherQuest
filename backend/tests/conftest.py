"""Shared test fixtures.

``DATABASE_URL`` is pinned *before* the application is imported so the engine
never touches a developer's real database. Each test gets a clean schema plus
freshly seeded mission content.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

os.environ["DATABASE_URL"] = "sqlite:///./data/test_cipherquest.db"
os.environ["APP_ENV"] = "test"
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SESSION_HEADER = "X-Session-Token"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """A TestClient on an empty, freshly seeded database."""
    from app.core.database import Base, engine
    from app.main import app

    Base.metadata.drop_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

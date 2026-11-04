"""Alembic environment for CipherQuest.

The connection string always comes from application settings (``DATABASE_URL``)
rather than being hard-coded into ``alembic.ini``, so migrations target
whichever database the shell is configured for.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app import models  # noqa: E402,F401  (registers every table)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Honour an explicit URL from the CLI first, then application settings.
url = os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().database_url
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without a live database connection."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot DROP/ALTER many constraints in place.
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

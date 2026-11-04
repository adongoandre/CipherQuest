"""Database seeding command.

Creates the schema if it does not exist, then upserts every verified seed
mission. Safe to run repeatedly — upserts key on ``slug``.

    python -m scripts.seed            # create tables + upsert missions
    python -m scripts.seed --reset    # drop everything first (destructive)
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import Base, SessionLocal, engine
from app.seed import mission_count, seed_missions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the CipherQuest database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables first. Destroys existing data.",
    )
    args = parser.parse_args(argv)

    if args.reset:
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables.")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        before = mission_count(db)
        counts = seed_missions(db)
        after = mission_count(db)
    finally:
        db.close()

    print(
        f"Seeded missions: {counts['created']} created, {counts['updated']} updated "
        f"({before} -> {after} rows)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

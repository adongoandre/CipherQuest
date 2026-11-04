"""Mission content validation command.

Fails (exit code 1) when:

* any authoring definition has a content problem,
* a ciphertext cannot be reproduced from the stored plaintext, cipher and
  parameter,
* accepted riddle answers disagree about the resulting shift,
* a database row's ciphertext/parameter differs from what the engine derives,
* a published mission is missing hints, an explanation or a worked example.

Run it in CI and before every publish::

    python -m scripts.validate_missions
"""

from __future__ import annotations

import argparse
import sys

from app.cipher import decrypt, encrypt
from app.content import MISSION_DEFINITIONS, all_missions, apply_key_rule, validate_definition


def check_definitions() -> list[str]:
    """Validate every authored mission definition."""
    problems: list[str] = []
    for definition in MISSION_DEFINITIONS:
        for issue in validate_definition(definition):
            problems.append(f"[{definition.slug}] {issue}")
    return problems


def check_generated() -> list[str]:
    """Prove each generated mission's ciphertext round-trips to its plaintext."""
    problems: list[str] = []
    try:
        missions = all_missions()
    except ValueError as exc:
        return [str(exc)]

    for mission in missions:
        slug = mission["slug"]
        shift = mission["parameter"]
        plaintext = mission["plaintext_answer"]
        ciphertext = mission["ciphertext"]

        if encrypt(plaintext, shift) != ciphertext:
            problems.append(
                f"[{slug}] ciphertext does not match encrypt(plaintext, {shift})"
            )
        if decrypt(ciphertext, shift) != plaintext:
            problems.append(f"[{slug}] decrypt(ciphertext, {shift}) != stored plaintext")
        if apply_key_rule(mission["key_rule_id"], mission["accepted_riddle_answers"][0]) != shift:
            problems.append(f"[{slug}] parameter disagrees with the published key rule")
        if len(mission["hints"]) != 3:
            problems.append(f"[{slug}] expected exactly three hints")
        if not str(mission["explanation"]).strip():
            problems.append(f"[{slug}] missing explanation")
        if not str(mission["worked_example"]).strip():
            problems.append(f"[{slug}] missing worked example")
        if len(ciphertext) != len(plaintext):
            problems.append(
                f"[{slug}] ciphertext length {len(ciphertext)} != plaintext length "
                f"{len(plaintext)} (Caesar preserves length)"
            )
    return problems


def check_database() -> list[str]:
    """Compare published database rows against freshly generated content."""
    try:
        from sqlalchemy import select

        from app.core.database import SessionLocal
        from app.models import Mission, PublicationStatus
    except Exception as exc:  # pragma: no cover - import guards
        return [f"database unavailable: {exc}"]

    generated = {m["slug"]: m for m in all_missions()}
    problems: list[str] = []

    db = SessionLocal()
    try:
        rows = list(db.scalars(select(Mission).where(
            Mission.status == PublicationStatus.PUBLISHED
        )).all())
    finally:
        db.close()

    for row in rows:
        source = generated.get(row.slug)
        if source is None:
            problems.append(f"[{row.slug}] published in the database but not in content")
            continue
        if row.ciphertext != source["ciphertext"]:
            problems.append(
                f"[{row.slug}] database ciphertext differs from the generated ciphertext"
            )
        if row.parameter != source["parameter"]:
            problems.append(f"[{row.slug}] database parameter differs from the key rule")
        if row.plaintext_answer != source["plaintext_answer"]:
            problems.append(f"[{row.slug}] database plaintext differs from content")
        if len(row.hints or []) != 3:
            problems.append(f"[{row.slug}] database row does not have exactly three hints")

    missing = set(generated) - {r.slug for r in rows}
    for slug in sorted(missing):
        problems.append(f"[{slug}] present in content but not published in the database")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CipherQuest mission content.")
    parser.add_argument(
        "--skip-database",
        action="store_true",
        help="Only validate authored content; do not compare against the database.",
    )
    args = parser.parse_args(argv)

    problems = check_definitions() + check_generated()
    if not args.skip_database:
        problems += check_database()

    if problems:
        print(f"MISSION VALIDATION FAILED ({len(problems)} problem(s)):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    count = len(MISSION_DEFINITIONS)
    print(f"OK: {count} missions verified - ciphertext reproduces from plaintext + parameter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

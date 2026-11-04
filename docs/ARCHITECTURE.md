# CipherQuest — architecture

Week 1 MVP: one complete, playable mission loop with a tested cipher engine and
seeded content. This document records how it is put together and why.

## Stack

| Layer | Choice |
| --- | --- |
| API | FastAPI + Pydantic v2, SQLAlchemy 2 (ORM), Alembic migrations |
| Database | SQLite locally / in tests; PostgreSQL is the production target (`DATABASE_URL`) |
| Content | Python module (`app/content`) — versioned, validated, seeded into the DB |
| Frontend | Vite + React 19 + TypeScript, React Router 7 |
| Styling | Hand-written CSS design system (`src/styles.css`), no UI framework |
| Tests | pytest (backend), Vitest + Testing Library (frontend) |

## Shape

```
browser (React SPA)
   │  fetch /api/v1/*  ·  X-Session-Token header
   ▼
Vite dev proxy ──► FastAPI
                     ├── api/v1/*      HTTP layer: validation, stage gating, errors
                     ├── services/     mission flow · scoring · analytics (rules live here)
                     ├── cipher/       Caesar engine + answer normalisation (pure functions)
                     ├── content/      mission definitions + key-rule registry
                     ├── models/       SQLAlchemy tables
                     └── core/         settings · database · structured logging
                     ▼
                   SQLite / Postgres
```

The layering is deliberate: routes never compute a score or decide a stage, and the
cipher module knows nothing about HTTP. Everything the player-visible rules depend on
is a pure function with its own tests.

## Data model

- **PlayerSession** — pseudonymous guest, identified by a token (`X-Session-Token`).
  `POST /auth/register` upgrades the same row into an account (display name, email,
  password hash) without losing progress; `POST /account/delete` deletes it and every
  child row cascades away.
- **Mission** — content row: riddle, accepted answers, key rule (description + numeric
  parameter, surfaced only after the riddle via `KeyReveal`'s `accepted_answer`,
  `key_type`, `parameter`, `key_rule_description`), contextual clue,
  hints, ciphertext, plaintext, comprehension question, difficulty, timing.
- **Attempt** — one row per submission (stage, outcome, hints used, elapsed).
- **Progress** — one row per session × mission: stage reached, completed_at,
  hints_used, comprehension_awarded.
- **FeedbackSurvey** / **AnalyticsEvent** — optional engagement data; events store
  outcomes only, never typed answers.

## The mission loop

```
riddle ──correct──► key_reveal ──advance──► context_clue ──advance──► decrypt
   │                                                          │
   └──wrong: retry (attempts counted)                    wrong: retry
                                                              │ correct / reveal
                                                              ▼
                                                        explanation
                                                        (score + comprehension)
```

Every transition is enforced server-side: a request for content belonging to a later
stage returns `409` instead of the content, so the UI cannot leak the answer by
over-fetching. Snapshots are stage-gated for the same reason — reloading the page
rebuilds exactly what the player has earned the right to see.

## Key design decisions

**Ciphertext is generated, never hand-typed.** Each mission stores a key rule
(`letter_count`, `first_letter_position`, …) and its plaintext; encryption happens at
seed time. `python -m scripts.validate_missions` re-derives every ciphertext, checks
each accepted answer maps to a single shift, and fails on drift — a content edit can't
silently produce an unsolvable mission.

**Answer matching is normalisation, not string equality.** Riddle and decrypt answers
go through case folding, punctuation/whitespace stripping and plural handling, so
"Green Stone", "green-stone!" and "green stones" are one answer.

**Scores are server-authoritative.** The browser sends attempts and elapsed time; the
backend returns the breakdown (70 solve / 10 no-hint / 15 time / 5 comprehension,
max 100). The client only renders what it is given.

**Idempotency keys on attempts.** A double-clicked submit or a retried request can't
double-count an attempt or re-award a bonus.

**Guest-first, accounts optional.** Progress is tied to a rotating pseudonymous token
in `sessionStorage`, so the whole loop is playable with no account and the identifier
disappears with the tab. An account upgrades that same session row: register keeps
every attempt and score, login hands the token back, and `POST /account/delete`
cascades the row and all of its children away.

## Verification

- Backend: `pytest` — cipher engine, normalisation, scoring, content validation, API
  stage-gating and full-loop integration tests.
- Frontend: `vitest` — landing render and a scripted mission walkthrough that asserts
  no content from later stages is ever present.
- Manual: live HTTP walk of all 20 loop checks plus a browser session (submit, hint,
  decrypt, comprehension, reload-recovery).

## Deliberately out of scope for Week 1

Postgres in dev, rate limiting beyond configuration, and deployment. Each has a seam
already in place (`DATABASE_URL`, settings). Authentication, the weekly cup/rooms play
surfaces and the admin mission CMS have landed (`/auth`, `/compete`, `/rooms`,
`/admin`).

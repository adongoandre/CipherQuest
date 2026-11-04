# CipherQuest

An educational encryption game. Players read a riddle, derive a cipher parameter from
its answer, read a separate contextual clue, decrypt a message, and receive a worked
explanation of how the cipher worked.

Classical ciphers here are **teaching material only** — they are not suitable for
protecting real confidential information.

Built for the Week 1 MVP of the CipherQuest project proposal: one complete, playable
mission loop with a FastAPI backend, a React frontend, a tested Caesar cipher engine,
and seeded content.

---

## Quick start

Requires Python 3.11+ and Node 20+.

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # macOS/Linux: .venv/bin/pip
cp ../.env.example ../.env                        # adjust values if needed
.venv/Scripts/python -m scripts.seed              # create tables + load the 5 missions
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (second terminal)
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```

The backend also seeds automatically on first boot if the database is empty.
Interactive API docs: <http://127.0.0.1:8000/docs>

### Windows: one-click start

After the setup above, double-click **`start-cipherquest.bat`** (or the
`CipherQuest` shortcut on the Desktop). It opens the API and the web app in
their own windows, waits until both answer, then opens <http://localhost:5173>.
Anything already running is reused, so it is safe to run twice. Close the two
windows — or press `Ctrl+C` in each — to stop the application.

The Vite dev server proxies `/api` to `127.0.0.1:8000`, so no extra CORS setup is
needed locally (the backend still enforces `FRONTEND_ORIGIN`).

## Commands

| Task | Command |
| --- | --- |
| Run backend tests | `cd backend && .venv/Scripts/python -m pytest` |
| Run frontend tests | `cd frontend && npm test` |
| Frontend typecheck | `cd frontend && npm run typecheck` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend build | `cd frontend && npm run build` |
| Validate seed ciphertext | `cd backend && .venv/Scripts/python -m scripts.validate_missions` |
| Reseed content | `cd backend && .venv/Scripts/python -m scripts.seed` |
| Create a migration | `cd backend && .venv/Scripts/alembic revision --autogenerate -m "msg"` |
| Apply migrations | `cd backend && .venv/Scripts/alembic upgrade head` |

## Repository layout

```
backend/
  app/
    api/            error handlers, shared dependencies, v1 routers
    cipher/         Caesar engine + answer normalisation
    content/        mission definitions and key-rule registry (source of truth)
    core/           settings, database, logging
    models/         SQLAlchemy ORM models
    schemas/        Pydantic request/response models
    services/       mission flow, scoring, analytics
    seed.py         idempotent content seeding
  scripts/          seed + ciphertext validation entry points
  tests/            pytest suite
  alembic/          migrations
frontend/
  src/
    lib/api.ts      typed API client (guest session + account handling)
    pages/          Landing, Cipher lab, Missions, Mission, Progress, Help
    components/     Dispatch, HintPanel, ScoreCard, FeedbackSurvey
    test/           Vitest + Testing Library suite
docs/               API reference and architecture notes
```

## How a mission plays

1. **Riddle** — the player answers the riddle; accepted variants are normalised
   (case, punctuation, whitespace, pluralisation) before comparison.
2. **Key** — the accepted answer is transformed by the mission's key rule into the
   Caesar shift. The key rule is revealed only after a correct riddle answer, in a
   `key_reveal` payload of `{accepted_answer, key_type, parameter, key_rule_description}`.
3. **Clue** — contextual flavour text plus progressive hints (each hint costs the
   no-hint bonus; revealed hints survive a page reload).
4. **Decrypt** — the player submits plaintext; it is checked server-side with the
   same normalisation as the riddle.
5. **Explanation** — a worked decryption, the score breakdown, and an optional
   5-point comprehension question. Reveal-solution is available as an escape hatch
   and awards no points.

Scoring (server-authoritative, 100 max): 70 correct decryption, up to 10 no-hint
bonus, up to 15 time bonus on timed missions, 5 comprehension.

## Documentation

- [docs/API.md](docs/API.md) — endpoint reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — structure, data flow, decisions
- `CipherQuest_Project_Proposal.docx` / `CipherQuest_MVP_Master_Prompt.docx` — brief

# CipherQuest API reference

Base URL (local): `http://127.0.0.1:8000`
Interactive docs: `/docs` (Swagger) · `/redoc`

All routes are versioned under `/api/v1`.

## Conventions

- **Sessions and accounts.** Every request resolves or creates a pseudonymous player
  session from the `X-Session-Token` header; the server returns a fresh token in the
  same response header when it creates one. The frontend stores the token in
  `sessionStorage` (it disappears when the tab closes) and sends it on every call.
  Play is guest-first — an account is optional: `POST /auth/register` upgrades the
  current guest session in place (keeping all progress), `POST /auth/login` returns
  its token, and `POST /account/delete` removes the account and everything under it.
- **Stage gating.** A mission moves through `riddle → key → context_clue → decrypt →
  explanation`. Out-of-order calls return `409` with `{"code": "stage_not_advanceable"}`
  (or an equivalent code) instead of leaking later content.
- **Idempotency.** Attempt endpoints accept an optional `idempotency_key`; replaying a
  key returns the original outcome without double-counting.
- **Errors.** Failures share one envelope:
  `{"error": {"code": "...", "message": "...", "details": {...}}}` with a matching
  HTTP status (`400` validation, `404` missing, `409` state conflict).
- **Content negotiation.** Extra request fields are rejected (`extra="forbid"`).

## Endpoints

### System

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service banner (not in OpenAPI) |
| `GET` | `/api/v1/health` | Liveness + database check → `{status, app_env, database, version, time}` |

### Session

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/session` | Create or resume a guest session → `{token, display_name, created}` |

### Missions

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/missions` | List published missions + `daily_slug` → `{missions[], daily_slug}` |
| `GET` | `/api/v1/missions/daily` | Today's mission snapshot (records `mission_started`) |
| `GET` | `/api/v1/missions/{ident}` | Mission snapshot by id or slug (records `mission_started`) |

A **snapshot** is stage-gated: it always includes `stage`, the current stage's
content, `hints_revealed`, and — only once the mission is at `explanation` — the
`earned` score and `comprehension_awarded` flag, so a reload reconstructs the exact
screen without replaying attempts.

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/missions/{ident}/riddle-attempt` | `{answer, idempotency_key?}` | Check the riddle; on success returns `key_reveal` |
| `POST` | `/api/v1/missions/{ident}/advance` | — | `key → context_clue` then `context_clue → decrypt`; returns clue/ciphertext |
| `POST` | `/api/v1/missions/{ident}/hint` | — | Reveal the next hint → `{hint_number, total_hints, hint, hints_used, score_penalty_note}` |
| `POST` | `/api/v1/missions/{ident}/decrypt-attempt` | `{answer, elapsed_seconds?, idempotency_key?}` | Check plaintext; on success returns `score` breakdown, `solution`, and the comprehension question |
| `POST` | `/api/v1/missions/{ident}/reveal` | `{reason: "stuck"\|"finished"}` | Show the solution with `score_awarded: 0` |
| `POST` | `/api/v1/missions/{ident}/comprehension` | `{choice, idempotency_key?}` | Check the 5-point question → `{correct, earned, total, correct_index, explanation, awarded}` |

`key_reveal` appears only after a correct riddle answer (the field is absent while the
riddle is open) and carries the whole key contract:

```json
{"accepted_answer": "CLOCK", "key_type": "letter_count", "parameter": 5,
 "key_rule_description": "Count the letters in your riddle answer. That number is the Caesar shift."}
```

- `accepted_answer` — the normalised answer that was accepted;
- `key_type` — which key rule produced the parameter;
- `parameter` — the numeric parameter (here the Caesar shift);
- `key_rule_description` — the human-readable rule shown on the “key revealed” and
  decrypt panels.

### Progress

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/progress` | Session totals + per-mission completion/score → `{progress, missions[]}` |

### Engagement

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/feedback` | `{mission_slug, clarity_rating?, learned?, enjoyment_rating?, would_return?, comment?}` | Optional post-mission survey → `{saved, message}` |
| `POST` | `/api/v1/analytics` | `{event_name, ...}` | Client event. Recorded server-side: `mission_started`, `key_revealed`, `context_clue_viewed`, `hint_used`, `mission_completed`, `solution_revealed`, `comprehension_answered`, `feedback_submitted`. Only outcomes are stored, never typed answers |

### Account

Optional on top of the guest session; same `X-Session-Token` header mechanics.

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | `{display_name, email, password, accepted_terms}` | Upgrade the current guest session into an account, keeping all progress → `{token, display_name, created}` |
| `POST` | `/api/v1/auth/login` | `{email, password}` | Verify credentials and hand back the account session's token → `{token, display_name, created}` |
| `GET` | `/api/v1/auth/me` | — | The signed-in identity → profile |
| `POST` | `/api/v1/account/delete` | — | Delete the signed-in player's account and every row that belongs to it (attempts, lessons, friendships and cup entries cascade from the session; audit references are nulled) → `{deleted, message}` |

### Admin (admin sessions only)

A non-admin session gets `403` with `{"code": "admin_required"}`.

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/admin/missions/{mission_id}` | `MissionDraftRequest` (full draft, same shape as create) | Save a draft edit of an existing mission. Ciphertext, the explanation and the worked example are rebuilt from the plaintext and the first accepted answer's letter count; unknown id → `404 mission_not_found`, duplicate title → `409 slug_exists`; every save writes an audit entry → `AdminMissionDetail` |

Sibling admin routes: `GET`/`POST` `/api/v1/admin/missions`,
`GET` `/api/v1/admin/missions/{id}`, `POST /api/v1/admin/missions/{id}/verify|publish|retire`,
and `GET` `/api/v1/admin/audit`.

## Scoring (server-authoritative)

| Component | Points |
| --- | --- |
| Correct decryption | 70 |
| No-hint bonus (zero hints used) | 10 |
| Time bonus (timed missions only, linear to target) | 0–15 |
| Comprehension question | 5 |
| **Maximum** | **100** |

Reveal-solution awards 0. The client never computes a score it is not later given
back by the server.

## Sample flow

```bash
# 1. Session (save the token from the X-Session-Token response header)
curl -i -X POST http://127.0.0.1:8000/api/v1/session

# 2. Mission snapshot
curl -H "X-Session-Token: $TOKEN" http://127.0.0.1:8000/api/v1/missions/midnight-clock

# 3. Riddle → key
curl -X POST -H "X-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"answer":"clock"}' http://127.0.0.1:8000/api/v1/missions/midnight-clock/riddle-attempt

# 4. Clue, then ciphertext
curl -X POST -H "X-Session-Token: $TOKEN" http://127.0.0.1:8000/api/v1/missions/midnight-clock/advance
curl -X POST -H "X-Session-Token: $TOKEN" http://127.0.0.1:8000/api/v1/missions/midnight-clock/advance

# 5. Decrypt
curl -X POST -H "X-Session-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"answer":"...","elapsed_seconds":42}' \
  http://127.0.0.1:8000/api/v1/missions/midnight-clock/decrypt-attempt
```

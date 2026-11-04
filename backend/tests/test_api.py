"""End-to-end API tests for the mission loop.

These exercise the application the way the browser will: through HTTP, with a
real database session per test, asserting both behaviour *and* that protected
fields never appear before their stage.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.cipher import decrypt

SESSION_HEADER = "X-Session-Token"
SLUG = "midnight-clock"
PLAINTEXT = "Count the hours aloud from midnight until the ferry touches the north quay"


def new_session(client: TestClient) -> dict[str, str]:
    """Create a guest session and return the headers for later requests."""
    response = client.post("/api/v1/session")
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert response.headers.get(SESSION_HEADER) == token
    return {SESSION_HEADER: token}


def _correct_index(slug: str) -> int:
    """Read the published correct choice straight from the content module."""
    from app.content import MISSION_DEFINITIONS

    definition = next(d for d in MISSION_DEFINITIONS if d.slug == slug)
    return int(definition.story.comprehension["correct_index"])


def solve_riddle(client: TestClient, headers: dict[str, str]) -> dict:
    """Submit the correct riddle answer and return the response body."""
    riddle = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": "CLOCK"},
        headers=headers,
    )
    assert riddle.status_code == 200, riddle.text
    assert riddle.json()["correct"] is True
    reveal = riddle.json()["key_reveal"]
    assert reveal["accepted_answer"] == "CLOCK"
    # Once solved, the reveal hands over the worked-out key (rule + shift).
    assert reveal["parameter"] == 5
    assert reveal["key_rule_description"]
    return riddle.json()


def advance(client: TestClient, headers: dict[str, str]) -> dict:
    """POST /advance once and return the body."""
    response = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def walk_to_clue(client: TestClient, headers: dict[str, str]) -> dict:
    """Riddle -> key reveal -> contextual clue."""
    solve_riddle(client, headers)
    return advance(client, headers)


def walk_to_decrypt(client: TestClient, headers: dict[str, str]) -> dict:
    """Continue from the clue to the ciphertext."""
    walk_to_clue(client, headers)
    return advance(client, headers)


# --- health & session -----------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"].endswith(":ok")


def test_session_is_created_and_echoed_as_a_header(client: TestClient) -> None:
    response = client.post("/api/v1/session")
    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert len(body["token"]) == 32
    assert response.headers[SESSION_HEADER] == body["token"]


def test_resuming_with_a_known_token_reuses_the_session(client: TestClient) -> None:
    headers = new_session(client)
    again = client.post("/api/v1/session", headers=headers)
    assert again.json()["created"] is False
    assert again.json()["token"] == headers[SESSION_HEADER]


def test_an_unknown_token_does_not_hijack_another_session(client: TestClient) -> None:
    real = new_session(client)
    forged = client.post("/api/v1/session", headers={SESSION_HEADER: "f" * 32})
    assert forged.json()["token"] != real[SESSION_HEADER]


# --- mission payload gating ----------------------------------------------


def test_mission_list_exposes_no_secrets(client: TestClient) -> None:
    headers = new_session(client)
    body = client.get("/api/v1/missions", headers=headers).json()
    assert len(body["missions"]) == 5
    assert body["daily_slug"]
    for mission in body["missions"]:
        assert set(mission) == {
            "id", "slug", "title", "difficulty", "cipher_type",
            "estimated_minutes", "display_order", "is_completed",
        }


def test_riddle_stage_payload_leaks_nothing_protected(client: TestClient) -> None:
    headers = new_session(client)
    body = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()

    assert body["stage"] == "riddle"
    assert body["cipher_name"] == "Caesar Cipher"
    assert body["riddle_prompt"]

    forbidden = {
        "ciphertext", "plaintext_answer", "plaintext", "accepted_riddle_answers",
        "hints", "contextual_clue", "key_reveal", "solution", "explanation",
        "scoring_config", "parameter", "key_rule_description", "comprehension_check",
    }
    assert forbidden.isdisjoint(body.keys())


def test_unknown_mission_returns_a_structured_404(client: TestClient) -> None:
    headers = new_session(client)
    response = client.get("/api/v1/missions/no-such-mission", headers=headers)
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "mission_not_found"
    assert error["message"]


def test_mission_started_is_recorded_once(client: TestClient) -> None:
    from app.core.database import SessionLocal
    from app.models import AnalyticsEvent
    from sqlalchemy import func, select

    headers = new_session(client)
    client.get(f"/api/v1/missions/{SLUG}", headers=headers)
    client.get(f"/api/v1/missions/{SLUG}", headers=headers)

    db = SessionLocal()
    try:
        count = db.scalar(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.event_name == "mission_started"
            )
        )
    finally:
        db.close()
    assert count == 1


# --- riddle ----------------------------------------------------------------


def test_wrong_riddle_answer_does_not_reveal_the_key(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": "banana"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["key_reveal"] is None
    assert body["stage"] == "riddle"


@pytest.mark.parametrize("answer", ["clock", "CLOCK", "  clock  ", "watch"])
def test_accepted_riddle_variants_reveal_the_key(
    client: TestClient, answer: str
) -> None:
    headers = new_session(client)
    response = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": answer},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["key_reveal"] is not None
    assert body["key_reveal"]["accepted_answer"] == "CLOCK"
    assert body["key_reveal"]["key_type"] == "shift"
    # After solving, the reveal carries the worked-out key: the mockups show
    # the rule and the shift number on the key-reveal and decrypt screens.
    assert body["key_reveal"]["parameter"] == 5
    assert body["key_reveal"]["key_rule_description"]


def test_key_reveal_stage_carries_the_worked_out_shift(client: TestClient) -> None:
    headers = new_session(client)
    solve_riddle(client, headers)

    body = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    assert body["stage"] == "key_reveal"
    reveal = body["key_reveal"]
    assert reveal["accepted_answer"] == "CLOCK"
    assert reveal["parameter"] == 5
    assert reveal["key_rule_description"]
    assert body["telling_number"] == 1
    assert body["telling_count"] == 4


def test_empty_riddle_answer_fails_validation(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": ""},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# --- staged reveals --------------------------------------------------------


def test_clue_is_withheld_until_the_riddle_is_solved(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stage_not_advanceable"


def test_advance_reveals_clue_then_ciphertext_then_stops(client: TestClient) -> None:
    headers = new_session(client)
    solve_riddle(client, headers)

    clue = advance(client, headers)
    assert clue["stage"] == "context_clue"
    assert clue["contextual_clue"]
    assert clue["ciphertext"] is None

    message = advance(client, headers)
    assert message["stage"] == "decrypt"
    assert message["ciphertext"]

    done = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert done.status_code == 409


def test_ciphertext_decrypts_back_to_the_stored_plaintext(client: TestClient) -> None:
    headers = new_session(client)
    payload = walk_to_decrypt(client, headers)
    assert decrypt(payload["ciphertext"], 5) == PLAINTEXT


def test_stage_is_not_advanceable_before_riddle_solved(client: TestClient) -> None:
    headers = new_session(client)
    client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": "wrong"},
        headers=headers,
    )
    response = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert response.status_code == 409


# --- hints ------------------------------------------------------------------


def test_hints_reveal_progressively_and_usage_is_tracked(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)

    numbers = []
    for expected_number in (1, 2, 3):
        response = client.post(f"/api/v1/missions/{SLUG}/hint", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["hint_number"] == expected_number
        assert body["total_hints"] == 3
        assert body["hints_used"] == expected_number
        assert body["hint"]
        numbers.append(body["hint"])

    assert len(set(numbers)) == 3, "hints must be distinct"

    exhausted = client.post(f"/api/v1/missions/{SLUG}/hint", headers=headers)
    assert exhausted.status_code == 409
    assert exhausted.json()["error"]["code"] == "no_hints_remaining"


def test_reloading_the_mission_reports_hints_used(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(f"/api/v1/missions/{SLUG}/hint", headers=headers)

    body = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    assert body["stage"] == "decrypt"
    assert body["hints_revealed"] == 1
    assert body["hint_count_total"] == 3


# --- decrypt ----------------------------------------------------------------


def test_decrypt_is_locked_before_the_ciphertext_is_revealed(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decrypt_locked"


def test_incorrect_decryption_returns_no_solution(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    response = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": "this is definitely not it"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["solution"] is None
    assert body["score"] is None
    assert body["comprehension_check"] is None
    assert body["stage"] == "decrypt"


def test_correct_decryption_returns_solution_and_no_hint_score(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    response = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": f"  {PLAINTEXT.upper()}  "},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["correct"] is True
    assert body["stage"] == "explanation"
    assert body["progress_awarded"] is True
    assert body["solution"]["plaintext"] == PLAINTEXT
    assert body["solution"]["explanation"]
    assert "Caesar shift of 5" in body["solution"]["explanation"]
    assert body["solution"]["worked_example"]

    score = body["score"]
    assert score["solve_points"] == 70
    assert score["no_hint_bonus"] == 10
    assert score["time_bonus"] == 0
    assert score["total"] == 80

    # The comprehension question ships with the solution, never before it.
    check = body["comprehension_check"]
    assert check["question"]
    assert len(check["choices"]) >= 2
    assert 0 <= check["correct_index"] < len(check["choices"])
    assert check["explanation"]


def test_using_a_hint_costs_the_no_hint_bonus(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(f"/api/v1/missions/{SLUG}/hint", headers=headers)

    response = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )
    score = response.json()["score"]
    assert score["solve_points"] == 70
    assert score["no_hint_bonus"] == 0
    assert score["total"] == 70


def test_repeat_submission_with_the_same_key_cannot_double_award(
    client: TestClient,
) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)

    payload = {"answer": PLAINTEXT, "idempotency_key": "abc-123"}
    first = client.post(f"/api/v1/missions/{SLUG}/decrypt-attempt", json=payload,
                        headers=headers)
    second = client.post(f"/api/v1/missions/{SLUG}/decrypt-attempt", json=payload,
                         headers=headers)

    assert first.json()["progress_awarded"] is True
    assert second.json()["progress_awarded"] is False
    assert first.json()["score"]["total"] == second.json()["score"]["total"]

    progress = client.get("/api/v1/progress", headers=headers).json()["progress"]
    assert progress["total_score"] == 80
    assert progress["total_puzzles_solved"] == 1


def test_replays_do_not_multiply_xp_but_do_count_completions(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)

    for _ in range(3):
        response = client.post(
            f"/api/v1/missions/{SLUG}/decrypt-attempt",
            json={"answer": PLAINTEXT},
            headers=headers,
        )
        assert response.json()["score"]["total"] == 80

    progress = client.get("/api/v1/progress", headers=headers).json()["progress"]
    assert progress["total_score"] == 80, "XP must be granted exactly once"
    assert progress["total_puzzles_solved"] == 3
    assert progress["missions_completed"] == 1


# --- reveal & comprehension -------------------------------------------------


def test_reveal_returns_the_solution_without_scoring(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    response = client.post(
        f"/api/v1/missions/{SLUG}/reveal",
        json={"reason": "stuck"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["solution"]["plaintext"] == PLAINTEXT
    assert body["score_awarded"] == 0

    progress = client.get("/api/v1/progress", headers=headers).json()["progress"]
    assert progress["missions_completed"] == 0


def test_comprehension_check_awards_five_points_once(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )

    correct_index = _correct_index(SLUG)
    first = client.post(
        f"/api/v1/missions/{SLUG}/comprehension",
        json={"choice": correct_index},
        headers=headers,
    )
    assert first.status_code == 200
    body = first.json()
    assert body["correct_index"] == correct_index
    assert body["correct"] is True
    assert body["awarded"] is True
    assert body["earned"] == 5
    assert body["explanation"]

    again = client.post(
        f"/api/v1/missions/{SLUG}/comprehension",
        json={"choice": correct_index},
        headers=headers,
    )
    assert again.json()["awarded"] is False
    assert again.json()["correct"] is True

    progress = client.get("/api/v1/progress", headers=headers).json()["progress"]
    assert progress["total_score"] == 85


def test_comprehension_requires_the_explanation_stage(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    response = client.post(
        f"/api/v1/missions/{SLUG}/comprehension",
        json={"choice": 0},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "explanation_required"


# --- session isolation ------------------------------------------------------


def test_reloading_the_result_screen_returns_the_earned_score(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )

    payload = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    assert payload["stage"] == "explanation"
    assert payload["earned_score"]["total"] == 80
    assert payload["earned_score"]["solve_points"] == 70
    assert payload["earned_score"]["no_hint_bonus"] == 10
    assert payload["comprehension_check"]["question"]
    assert payload["comprehension_awarded"] is False


def test_a_revealed_solution_still_has_no_score_after_reload(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(
        f"/api/v1/missions/{SLUG}/reveal",
        json={"reason": "stuck"},
        headers=headers,
    )

    payload = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    assert payload["stage"] == "explanation"
    assert payload["earned_score"] is None
    assert payload["solution"]["plaintext"] == PLAINTEXT


def test_comprehension_award_survives_a_reload(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)
    client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )
    client.post(
        f"/api/v1/missions/{SLUG}/comprehension",
        json={"choice": 0},
        headers=headers,
    )

    payload = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    assert payload["comprehension_awarded"] is True


def test_progress_is_isolated_between_sessions(client: TestClient) -> None:
    alice = new_session(client)
    bob = new_session(client)

    walk_to_decrypt(client, alice)
    client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=alice,
    )

    bob_progress = client.get("/api/v1/progress", headers=bob).json()["progress"]
    assert bob_progress["missions_completed"] == 0
    assert bob_progress["total_score"] == 0

    alice_progress = client.get("/api/v1/progress", headers=alice).json()["progress"]
    assert alice_progress["missions_completed"] == 1


def test_anonymous_caller_still_gets_a_session_header(client: TestClient) -> None:
    response = client.get("/api/v1/missions")
    assert response.status_code == 200
    assert response.headers.get(SESSION_HEADER)


# --- feedback & analytics ---------------------------------------------------


def test_feedback_is_saved(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        "/api/v1/feedback",
        json={
            "mission_slug": SLUG,
            "clarity_rating": 5,
            "learned": "yes",
            "enjoyment_rating": 4,
            "would_return": "maybe",
            "comment": "Clear and fun.",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["saved"] is True


def test_empty_feedback_is_rejected(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        "/api/v1/feedback", json={"mission_slug": SLUG}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_feedback"


def test_feedback_for_an_unknown_mission_404s(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        "/api/v1/feedback",
        json={"mission_slug": "ghost", "clarity_rating": 3},
        headers=headers,
    )
    assert response.status_code == 404


def test_client_cannot_fabricate_server_side_events(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        "/api/v1/analytics",
        json={"event_name": "mission_completed"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "event_not_client_reportable"


def test_client_may_report_landing_view(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        "/api/v1/analytics", json={"event_name": "landing_view"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["recorded"] is True


def test_unknown_body_field_is_rejected(client: TestClient) -> None:
    headers = new_session(client)
    response = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": "clock", "score": 100},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# --- restart & alternative tellings ---------------------------------------


def test_restarting_an_unfinished_mission_resets_the_stage(client: TestClient) -> None:
    headers = new_session(client)
    walk_to_decrypt(client, headers)

    response = client.post(f"/api/v1/missions/{SLUG}/restart", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stage"] == "riddle"
    assert body["telling_number"] == 1, "an unfinished mission replays the same telling"
    assert body["telling_count"] == 4
    assert body["riddle_prompt"]
    # The stage really rewound: advancing before re-solving the riddle fails.
    locked = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert locked.status_code == 409


def test_replaying_a_solved_mission_serves_the_next_telling(client: TestClient) -> None:
    from app.content import MISSION_DEFINITIONS

    headers = new_session(client)
    original = client.get(f"/api/v1/missions/{SLUG}", headers=headers).json()
    walk_to_decrypt(client, headers)
    solved = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": PLAINTEXT},
        headers=headers,
    )
    assert solved.json()["progress_awarded"] is True

    replay = client.post(f"/api/v1/missions/{SLUG}/restart", headers=headers)
    assert replay.status_code == 200, replay.text
    body = replay.json()
    assert body["stage"] == "riddle"
    assert body["telling_number"] == 2
    assert body["narrative"] != original["narrative"]
    assert body["riddle_prompt"] != original["riddle_prompt"]

    # The second telling carries its own riddle, answer, message and hints.
    second = MISSION_DEFINITIONS[0].alternates[0]
    hint = client.post(f"/api/v1/missions/{SLUG}/hint", headers=headers)
    assert hint.status_code == 200, hint.text
    assert hint.json()["hint"] == second.hints[0]

    riddle = client.post(
        f"/api/v1/missions/{SLUG}/riddle-attempt",
        json={"answer": second.accepted_riddle_answers[0]},
        headers=headers,
    )
    assert riddle.status_code == 200, riddle.text
    assert riddle.json()["correct"] is True

    client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    message = client.post(f"/api/v1/missions/{SLUG}/advance", headers=headers)
    assert message.json()["stage"] == "decrypt"
    assert message.json()["ciphertext"]

    decrypt = client.post(
        f"/api/v1/missions/{SLUG}/decrypt-attempt",
        json={"answer": second.plaintext},
        headers=headers,
    )
    assert decrypt.status_code == 200, decrypt.text
    assert decrypt.json()["correct"] is True
    assert decrypt.json()["progress_awarded"] is False, "XP is granted only once"

    progress = client.get("/api/v1/progress", headers=headers).json()["progress"]
    assert progress["missions_completed"] == 1
    assert progress["total_puzzles_solved"] == 2
    assert progress["total_score"] == 80, "a replay must not multiply XP"

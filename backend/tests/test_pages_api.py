"""End-to-end tests for the new mockup-driven endpoints.

Covers Home, Join/auth, Profile/Settings, Compete (leaderboards + cup),
Friends, Academy, Rooms and the Admin editor.
"""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

SESSION_HEADER = "X-Session-Token"


def new_session(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/session")
    assert response.status_code == 200
    return {SESSION_HEADER: response.json()["token"]}


def register(
    client: TestClient,
    headers: dict[str, str],
    *,
    display_name: str = "CodeFox",
    email: str = "codefox@example.com",
    password: str = "s3cret-pass",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "display_name": display_name,
            "email": email,
            "password": password,
            "accepted_terms": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- Home -----------------------------------------------------------------

def test_home_returns_engagement_sections(client: TestClient) -> None:
    headers = new_session(client)
    response = client.get("/api/v1/home", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["greeting"]
    assert len(body["week_dots"]) == 7
    assert body["daily_mission"] is None or body["daily_mission"]["slug"]
    assert body["weekly_cup"]["week"].count("-W") == 1
    assert isinstance(body["weekly_cup"]["participants"], int)
    assert isinstance(body["invitations"], list)
    assert isinstance(body["friend_activity"], list)


def test_home_reflects_completed_lesson_progress(client: TestClient) -> None:
    headers = new_session(client)
    done = client.post("/api/v1/lessons/caesar/1/complete", headers=headers)
    assert done.status_code == 200

    body = client.get("/api/v1/home", headers=headers).json()
    assert body["continue_learning"] is not None
    assert body["continue_learning"]["cipher_slug"] == "caesar"
    assert body["continue_learning"]["step"] == 2


# --- Join / auth / profile / settings -------------------------------------

def test_register_login_profile_and_settings(client: TestClient) -> None:
    headers = new_session(client)
    register(client, headers)

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["display_name"] == "CodeFox"
    assert me["is_guest"] is False
    assert me["level"] >= 1
    assert len(me["badges"]) >= 5
    assert len(me["mastery"]) == 8

    # Settings: defaults, then a persisted toggle + display-name change.
    settings = client.get("/api/v1/settings", headers=headers).json()
    assert settings["accessibility"]["reduce_motion"] is False

    updated = client.post(
        "/api/v1/settings",
        headers=headers,
        json={
            "accessibility": {"reduce_motion": True},
            "privacy": {"show_display_name": False},
            "display_name": "CodeFox",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["accessibility"]["reduce_motion"] is True
    assert updated.json()["privacy"]["show_display_name"] is False

    # Login from a fresh session with the same credentials.
    fresh = new_session(client)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "codefox@example.com", "password": "s3cret-pass"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    me2 = client.get("/api/v1/auth/me", headers={SESSION_HEADER: token})
    assert me2.json()["display_name"] == "CodeFox"
    assert fresh  # sanity: distinct guest session exists

    # Duplicate display names are rejected outright.
    other = new_session(client)
    conflict = client.post(
        "/api/v1/auth/register",
        headers=other,
        json={
            "display_name": "codefox",
            "email": "other@example.com",
            "password": "s3cret-pass",
            "accepted_terms": True,
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "display_name_taken"


# --- Compete ---------------------------------------------------------------

def test_leaderboards_rank_demo_players(client: TestClient) -> None:
    headers = new_session(client)
    response = client.get(
        "/api/v1/compete/leaderboards", params={"scope": "all_time"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()

    names = [row["display_name"] for row in body["standings"]]
    assert names[0] == "Maya"
    assert body["standings"][0]["score"] == 460
    assert {"Kofi", "Ama", "Yaw"} <= set(names)
    assert body["you"] is None  # fresh guest has no score


def test_weekly_cup_entry_is_idempotent(client: TestClient) -> None:
    headers = new_session(client)
    first = client.post("/api/v1/compete/cup/enter", headers=headers)
    assert first.status_code == 200
    assert first.json()["entered"] is True

    second = client.post("/api/v1/compete/cup/enter", headers=headers)
    assert second.status_code == 200
    assert "already" in second.json()["message"].lower()

    cup = client.get("/api/v1/compete/cup", headers=headers).json()
    assert cup["you_entered"] is True
    assert cup["participants"] >= 4  # demo players are entered
    assert cup["standings"], "entered players should appear in the standings"


# --- Friends ---------------------------------------------------------------

def test_friend_request_and_listing(client: TestClient) -> None:
    headers = new_session(client)
    sent = client.post(
        "/api/v1/friends/request", headers=headers, json={"display_name": "Maya"}
    )
    assert sent.status_code == 200
    assert sent.json()["ok"] is True

    listing = client.get("/api/v1/friends", headers=headers).json()
    assert len(listing["requests_outgoing"]) == 1
    assert listing["requests_outgoing"][0]["display_name"] == "Maya"
    assert listing["requests_incoming"] == []
    assert listing["friends"] == []

    missing = client.post(
        "/api/v1/friends/request", headers=headers, json={"display_name": "Nobody"}
    )
    assert missing.status_code == 404


# --- Academy ---------------------------------------------------------------

def test_academy_tracks_lesson_and_completion(client: TestClient) -> None:
    headers = new_session(client)
    academy = client.get("/api/v1/lessons", headers=headers).json()
    assert len(academy["tracks"]) == 8
    assert academy["total_lessons"] == 40
    assert academy["suggested_next"] == "caesar"

    lesson = client.get("/api/v1/lessons/caesar/2", headers=headers).json()
    assert lesson["step"] == 2
    assert lesson["body"]
    # Examples are either static (input/output) or interactive (shift widget).
    assert lesson["example"] is None or (
        lesson["example"]["input"] or lesson["example"]["interactive"]
    )

    complete = client.post("/api/v1/lessons/caesar/2/complete", headers=headers).json()
    assert complete["completed"] is True
    assert complete["xp_awarded"] == 5

    # Completing twice must not double-award XP.
    again = client.post("/api/v1/lessons/caesar/2/complete", headers=headers).json()
    assert again["xp_awarded"] == 0

    track = client.get("/api/v1/lessons/caesar", headers=headers).json()
    assert track["lessons"][1]["completed"] is True

    missing = client.get("/api/v1/lessons/nope/1")
    assert missing.status_code == 404


# --- Rooms -----------------------------------------------------------------

def test_room_create_join_ready_start(client: TestClient) -> None:
    host = new_session(client)
    guest = new_session(client)

    created = client.post("/api/v1/rooms", headers=host, json={"mode": "team_escape"})
    assert created.status_code == 200
    room = created.json()
    assert len(room["code"]) == 7
    assert room["you_are_host"] is True
    assert room["max_players"] == 4

    joined = client.post(
        "/api/v1/rooms/join", headers=guest, json={"code": room["code"]}
    )
    assert joined.status_code == 200
    assert len(joined.json()["players"]) == 2

    # Cannot start before everyone is ready.
    early = client.post(f"/api/v1/rooms/{room['code']}/start", headers=host)
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "players_not_ready"

    assert client.post(
        f"/api/v1/rooms/{room['code']}/ready", headers=host, json={"ready": True}
    ).status_code == 200
    assert client.post(
        f"/api/v1/rooms/{room['code']}/ready", headers=guest, json={"ready": True}
    ).status_code == 200

    started = client.post(f"/api/v1/rooms/{room['code']}/start", headers=host)
    assert started.status_code == 200
    state = started.json()
    assert state["status"] == "in_progress"
    assert state["mission_slug"]

    # Unknown codes are a structured 404.
    assert client.get("/api/v1/rooms/AAA-BBB", headers=guest).status_code == 404


# --- Admin -----------------------------------------------------------------

def test_admin_editor_requires_admin_and_round_trips(
    client: TestClient, monkeypatch
) -> None:
    guest = new_session(client)
    forbidden = client.get("/api/v1/admin/missions", headers=guest)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "admin_required"

    monkeypatch.setenv("ADMIN_EMAILS", "keeper@cipherquest.test")
    admin = new_session(client)
    register(
        client,
        admin,
        display_name="Keeper",
        email="keeper@cipherquest.test",
    )

    listed = client.get("/api/v1/admin/missions", headers=admin)
    assert listed.status_code == 200
    assert len(listed.json()) >= 5  # seeded missions, all verified

    draft = client.post(
        "/api/v1/admin/missions",
        headers=admin,
        json={
            "title": "The Test Lantern Code",
            "narrative": "A lamp flickers in the archive room, hiding a written note.",
            "riddle_prompt": "What device lights a room when the sun goes down?",
            "accepted_riddle_answers": ["lamp"],
            "key_rule_description": "The number of letters in the riddle answer",
            "contextual_clue": "The light source itself holds the count you need.",
            "plaintext_answer": "MEET ME AT DAWN",
            "hints": ["Count the letters in your answer.", "Shift by that number."],
            "difficulty": "beginner",
            "cipher_type": "caesar",
            "estimated_minutes": 5,
        },
    )
    assert draft.status_code == 200, draft.text
    mission = draft.json()
    assert mission["status"] == "draft"
    assert mission["parameter"] == 4  # "lamp" has 4 letters
    assert mission["verification"]["verified"] is True
    assert mission["ciphertext"] != mission["plaintext_answer"]

    verified = client.post(
        f"/api/v1/admin/missions/{mission['id']}/verify", headers=admin
    ).json()
    assert verified["verified"] is True
    assert verified["round_trip_ok"] is True

    published = client.post(
        f"/api/v1/admin/missions/{mission['id']}/publish", headers=admin
    ).json()
    assert published["status"] == "published"

    audit = client.get("/api/v1/admin/audit", headers=admin).json()
    actions = [entry["action"] for entry in audit["entries"]]
    assert "create" in actions
    assert "publish" in actions


def test_admin_rejects_non_admin_mutations(client: TestClient) -> None:
    guest = new_session(client)
    create = client.post(
        "/api/v1/admin/missions",
        headers=guest,
        json={
            "title": "Nope Mission",
            "narrative": "A guest attempts to author a mission they should not author.",
            "riddle_prompt": "Should this request even be accepted by the server?",
            "accepted_riddle_answers": ["nope"],
            "contextual_clue": "The gatekeeper should reject this request outright.",
            "plaintext_answer": "SHOULD FAIL",
        },
    )
    assert create.status_code == 403
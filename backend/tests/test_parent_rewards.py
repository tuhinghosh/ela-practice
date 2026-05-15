"""Smoke test that /api/progress/parent surfaces the reward state.

Iter 6 fixed the streak math but the parent view never showed it.
This test asserts the wiring exists and that the streak value matches
the value the child dashboard sees, so the two views agree.
"""
from fastapi.testclient import TestClient

from backend.app.main import app


def _login_and_submit(client: TestClient) -> None:
    assert client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    ).status_code == 200

    submit = client.post(
        "/api/activities/nature-01/submit",
        json={
            "responses": [
                {"question_id": "q1", "answer_choice": "The oak tree's roots took the water"},
                {"question_id": "q2", "answer_choice": "Healthy things that help plants grow"},
                {"question_id": "q3", "answer_choice": "Determined"},
                {
                    "question_id": "q4",
                    "answer_text": "Lila did not give up because she tried moving the pot.",
                },
            ]
        },
    )
    assert submit.status_code == 200


def test_parent_progress_includes_rewards_block() -> None:
    with TestClient(app) as client:
        _login_and_submit(client)
        parent = client.get("/api/progress/parent").json()

    assert "rewards" in parent
    rewards = parent["rewards"]
    assert {"stars", "streak_days", "badges"}.issubset(rewards.keys())
    assert rewards["streak_days"] >= 1
    assert rewards["stars"] >= 0
    assert isinstance(rewards["badges"], list)


def test_parent_rewards_match_dashboard_rewards() -> None:
    """Both endpoints should reflect the same reward_state row so the
    parent and child views never disagree about streak/stars."""
    with TestClient(app) as client:
        _login_and_submit(client)
        dashboard = client.get("/api/dashboard").json()
        parent = client.get("/api/progress/parent").json()

    assert dashboard["rewards"]["streak_days"] == parent["rewards"]["streak_days"]
    assert dashboard["rewards"]["stars"] == parent["rewards"]["stars"]
    assert dashboard["rewards"]["badges"] == parent["rewards"]["badges"]


def test_parent_rewards_zero_before_any_submission() -> None:
    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200
        parent = client.get("/api/progress/parent").json()

    assert parent["rewards"]["stars"] == 0
    assert parent["rewards"]["streak_days"] == 0
    assert parent["rewards"]["badges"] == []

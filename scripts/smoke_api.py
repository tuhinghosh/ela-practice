"""API assertions for the disposable production-Docker smoke harness.

This script intentionally uses only the Python standard library. The shell
orchestrator starts the packaged application and calls this client twice:
before and after replacing the container while retaining its data volume.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


FIRST_PILOT_ID = "pilot-mystery-cat-01"


class SmokeFailure(RuntimeError):
    pass


class Client:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Optional[dict[str, Any]] = None,
    ) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SmokeFailure(f"{method} {path} returned {exc.code}: {detail}") from exc
        if not raw:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(raw)
        return raw.decode("utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def login(client: Client, username: str, password: str) -> None:
    payload = client.request(
        "/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    require(payload.get("authenticated") is True, "Login did not return authenticated=true.")


def build_submission(activity: dict[str, Any]) -> dict[str, Any]:
    responses = []
    for question in activity["questions"]:
        if question["type"] == "multiple-choice":
            choices = question.get("choices") or []
            require(bool(choices), f'{question["id"]} has no choices in packaged content.')
            responses.append(
                {"question_id": question["id"], "answer_choice": choices[0]}
            )
        else:
            responses.append(
                {
                    "question_id": question["id"],
                    "answer_text": (
                        "The passage gives clear details that support this answer "
                        "and explain what the character learned."
                    ),
                }
            )
    return {"responses": responses}


def initial_phase(
    client: Client,
    username: str,
    password: str,
    state_file: Path,
) -> None:
    login(client, username, password)

    dashboard = client.request("/api/dashboard")
    require(
        dashboard["mission"]["activity_id"] == FIRST_PILOT_ID,
        "Fresh packaged app did not recommend the first pilot.",
    )
    require(
        dashboard["recommendation"]["decision"] == "complete-baseline",
        "Fresh packaged app did not expose the baseline recommendation reason.",
    )
    require(
        "choose any reviewed activity" in dashboard["recommendation"]["reason"],
        "Fresh packaged app presented its starter suggestion as mandatory.",
    )

    activity = client.request(f"/api/activities/{FIRST_PILOT_ID}")
    require(activity["id"] == FIRST_PILOT_ID, "Packaged pilot content is missing.")
    submission = client.request(
        f"/api/activities/{FIRST_PILOT_ID}/submit",
        method="POST",
        payload=build_submission(activity),
    )
    session_id = submission.get("session_id")
    require(bool(session_id), "Submission did not return a session id.")

    result = client.request(f"/api/sessions/{session_id}")
    require(
        len(result.get("question_results", [])) == len(activity["questions"]),
        "Saved result does not include every question review.",
    )
    require(
        all(item.get("skill_tag") for item in result["question_results"]),
        "Saved result is missing question-level skill evidence.",
    )
    require(
        all(item.get("explanation") for item in result["question_results"]),
        "Saved result is missing instructional explanations.",
    )

    next_dashboard = client.request("/api/dashboard")
    require(
        next_dashboard["mission"]["activity_id"] != FIRST_PILOT_ID,
        "Dashboard repeated the completed starter instead of suggesting another activity.",
    )
    require(
        next_dashboard["recommendation"]["attempts"] == 1,
        "Dashboard did not count the completed reviewed starter.",
    )
    require(
        FIRST_PILOT_ID in next_dashboard["completed_activity_ids"],
        "Dashboard did not expose the durable completed activity id.",
    )

    html = client.request("/")
    require(
        "Reading &amp; Writing" in html and "_next/static" in html,
        "FastAPI did not serve the packaged Next.js application.",
    )
    state_file.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "activity_id": FIRST_PILOT_ID,
                "recommended_activity_id": next_dashboard["mission"]["activity_id"],
            }
        ),
        encoding="utf-8",
    )
    print("✓ Login, packaged frontend, submission, feedback, and next mission verified")


def restart_phase(
    client: Client,
    username: str,
    password: str,
    state_file: Path,
) -> None:
    require(state_file.is_file(), "Smoke state file is missing before restart check.")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    login(client, username, password)

    result = client.request(f'/api/sessions/{state["session_id"]}')
    require(
        result["activity_id"] == state["activity_id"],
        "Saved session was not available after container replacement.",
    )
    dashboard = client.request("/api/dashboard")
    require(
        any(
            session["session_id"] == state["session_id"]
            for session in dashboard["recent_sessions"]
        ),
        "Persisted session is absent from the dashboard after restart.",
    )
    require(
        dashboard["mission"]["activity_id"] == state["recommended_activity_id"],
        "Recommendation state did not survive container replacement.",
    )
    require(
        state["activity_id"] in dashboard["completed_activity_ids"],
        "Completed activity state did not survive container replacement.",
    )
    print("✓ Database persistence and recommendation state survived replacement")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--phase", choices=("initial", "restart"), required=True)
    args = parser.parse_args()

    client = Client(args.base_url)
    if args.phase == "initial":
        initial_phase(client, args.username, args.password, args.state_file)
    else:
        restart_phase(client, args.username, args.password, args.state_file)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"SMOKE FAILURE: {exc}")
        raise SystemExit(1)

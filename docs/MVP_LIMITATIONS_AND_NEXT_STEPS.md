# MVP limitations and next steps

## Current state

ELA is a working local-first MVP for 3rd-grade reading/writing practice. It runs
as a single Docker container (FastAPI + static NextJS export + SQLite, port
8000) with OpenRouter for AI coaching. End-to-end flows work: login, browsing
50+ seeded activities across 10 themes and 8 skill tags, completing MC and
short-response questions, deterministic scoring with rubric and per-skill
breakdown, post-submission AI coach, reward state (stars/streak/badges), child
dashboard, and parent progress view. Backend pytest, frontend Vitest, and
Playwright E2E suites are in place.

## Known limitations

- Authentication is intentionally fixed to one local account (`user` / `password`).
- Content library is intentionally small and file-seeded for fast iteration.
- Adaptive difficulty is basic and does not perform formal assessment calibration.
- AI coach is constrained to post-submission support only in MVP.
- Data persistence is local SQLite only; no cloud sync or multi-device support.
- Parent analytics are intentionally lightweight and do not include deep reporting.

## Top gaps before the app is deployable

These are the gaps that block moving beyond a single-user local install. They
extend the limitations above with the specific blockers surfaced during review.

### 1. No real user management

One hardcoded user/password is checked in `backend/app/main.py` and a single
child profile is seeded in `backend/app/db.py`. There is no signup, password
hashing, multi-tenant isolation, or separation between parent and child roles.
Every install shares the same identity, so multiple families or multiple kids
in one family cannot use the app independently.

Next steps:
- Add user signup/login with hashed passwords (e.g. `argon2` or `bcrypt`).
- Introduce parent and child roles with distinct capabilities and UI.
- Support multiple child profiles per parent account.
- Scope every query by `user_id` / `child_profile_id` and add tests that prove
  cross-tenant isolation.

### 2. Insecure auth and secrets posture

`SESSION_SECRET` defaults to a known dev value in `backend/app/main.py`, the
OpenRouter API key lives in a project-root `.env`, and there is no HTTPS
assumption, CSRF protection, or login rate limiting. This posture is unsafe
for anything beyond `localhost`.

Next steps:
- Require `SESSION_SECRET` from the environment with no insecure fallback;
  fail fast at startup if missing.
- Move secrets to a deployment-appropriate store (Docker secrets, cloud secret
  manager) and document the rotation procedure.
- Add CSRF protection for state-changing endpoints and login attempt rate
  limiting / lockout.
- Enforce HTTPS in production (secure cookies, HSTS) and document the reverse
  proxy expectation.

### 3. Local SQLite with no migration or backup story

The database lives at `backend/data/ela.sqlite3` inside the container. The
schema is created with `CREATE TABLE IF NOT EXISTS` only — there is no
migration tooling, no documented volume mount, no backup workflow, and no
multi-device sync. Re-deploys risk data loss and there is no per-environment
config separation.

Next steps:
- Introduce a migration tool (e.g. `alembic` or hand-rolled versioned scripts)
  and check in an initial baseline.
- Document a persistent volume mount for `backend/data/` and a backup /
  restore procedure.
- Decide on a longer-term storage target (managed Postgres, Litestream, etc.)
  before opening the app beyond a single household.
- Separate dev / staging / prod configuration via environment variables.

### 4. Progress tracking is shallow

`progress_snapshots` is append-only with a flat strengths / growth-areas list.
There are no time-windowed trends, no per-skill mastery curves, no goal-setting,
and no surfacing of per-question history. The streak field in
`backend/app/db.py` is derived from `reward_state.updated_at`, which tracks the
last reward update rather than distinct daily activity, so the streak is
mis-defined.

Next steps:
- Track a dedicated `last_active_date` per child and compute streaks from
  distinct activity days.
- Add per-skill rolling averages with time windows (7-day, 30-day) and expose
  trend charts to parents.
- Surface per-question history (which questions a child has seen, missed, and
  retried) and use it to inform recommendations.
- Add parent-set goals (e.g. "3 activities per week", "improve inference")
  with progress against them.

### 5. No operability or observability

There is no structured logging, error tracking, metrics, or AI-cost guardrails
— OpenRouter calls are unbounded per session. The container has no real
healthcheck beyond process start, no CI deploy pipeline, and no content update
workflow (activities ship inside the frontend bundle, so any content change
requires a full rebuild).

Next steps:
- Add structured JSON logging with request IDs and error tracking
  (e.g. Sentry) in the backend.
- Add a `/api/health` endpoint that checks DB connectivity and (optionally)
  OpenRouter reachability, and wire it into the container healthcheck.
- Track AI usage per user/session and add daily / per-request budget caps with
  graceful degradation.
- Move seeded content out of the frontend bundle (serve from backend or load
  from a mounted directory) so content updates do not require a frontend
  rebuild.
- Add a CI pipeline that runs the existing pytest / Vitest / Playwright suites
  and builds the Docker image on every push.

## Practical next steps after MVP

These remain valuable once the deployability gaps above are addressed.

- Expand content set by skill and reading level with more variety.
- Improve deterministic writing rubric checks and add richer feedback templates.
- Add stronger per-skill trend views and parent goal-setting controls.
- Add optional constrained hint mode during activities (without answer leakage).
- Introduce account/profile expansion beyond one local user flow.
- Add deployment options after local home-use workflow is stable.

Your job is to make the app safely deployable and more useful for parent-guided ELA practice. Do not rewrite the app from scratch. Improve it incrementally, preserve working behavior, and leave the repo in a better tested state after every loop.

Current app summary:
- Single Docker container: FastAPI backend + static NextJS export + SQLite, served on port 8000
- OpenRouter used for post-submission AI coaching
- Current features: hardcoded login, seeded activities, deterministic scoring, AI coach panel, rewards, child dashboard, parent progress view, SQLite schema, pytest/Vitest/Playwright tests
- Main gaps:
  1. No real user management
  2. Insecure auth/secrets posture
  3. Container-bound SQLite with no volume/migrations/backups
  4. Shallow progress tracking and incorrect streak logic
  5. No operability/observability/cost guardrails/content workflow

Operating rules:
1. Work in small, shippable vertical slices.
2. At the start of each run, inspect the repo, git status, tests, and any existing progress files.
3. Maintain or create `RALPH_PROGRESS.md`.
4. Pick exactly one meaningful task per run unless a task is tiny and tightly coupled to another.
5. Do not break existing tests. Add tests for every behavior change.
6. Prefer simple, boring, maintainable solutions.
7. Do not introduce cloud dependencies unless absolutely necessary.
8. Do not expose child data externally except for the existing OpenRouter coaching flow.
9. Do not log child free-text responses or secrets.
10. Do not claim completion unless tests pass or you clearly document what failed and why.

Primary product constraint:
This is currently a family app, not a public SaaS product. Build toward safe private deployment first: real auth, persistent data, backups, config hygiene, and parent-visible progress. Avoid over-engineering enterprise multi-tenancy unless needed for parent/child separation and data isolation.

Backlog priority order:

P0: Deployment safety foundation
A. Replace hardcoded auth with real local user management:
   - Password hashing using a standard library
   - Parent and child roles
   - Seed/admin bootstrap flow via environment variable or first-run setup
   - Remove hardcoded `user/password`
   - Ensure child profile belongs to a parent/account
   - Tests for login success/failure, role access, and tenant isolation

B. Secure config/secrets:
   - No insecure default `SESSION_SECRET`
   - Validate required env vars at startup
   - Server-only OpenRouter key handling
   - Secure cookie settings configurable by environment
   - Basic CSRF protection for state-changing routes if cookie auth is used
   - Rate limit login attempts
   - Add `.env.example` with safe placeholders
   - Ensure `.env` is ignored by git
   - Tests for missing config and login rate limiting where practical

C. Persistent SQLite and migrations:
   - Make database path configurable
   - Add Docker volume guidance / docker-compose setup
   - Add migrations using a simple migration tool or a clear versioned migration runner
   - Preserve existing schema/data
   - Add backup/export command or documented script
   - Add migration tests or at minimum a smoke test from empty DB to usable DB

P1: Parent-useful learning progress
D. Fix streak logic:
   - Streak should be based on completed learning activity dates, not generic `updated_at`
   - Define what counts as a learning day
   - Add tests for same-day activity, consecutive days, skipped day, and timezone handling

E. Improve progress tracking:
   - Track per-skill performance over time
   - Add time-windowed summaries: 7-day, 30-day, all-time
   - Add parent-facing “what to practice next”
   - Surface recent question history and common growth areas
   - Keep it simple and explainable, not a black-box mastery model unless justified
   - Add backend tests and at least one frontend test for parent progress display

P2: Operability and content workflow
F. Observability:
   - Add structured logging
   - Add `/health` and `/ready`
   - Add basic request/error logging without child response text
   - Add AI call logging for count/cost/latency without sensitive content
   - Add guardrails for max AI calls per session/day

G. Content workflow:
   - Move seeded activities out of the frontend bundle if currently bundled there
   - Create versioned JSON/YAML activity files or backend seed files
   - Add validation for activities
   - Add a repeatable content import/update command
   - Add tests to validate all seeded activities

Per-run workflow:
1. Read `RALPH_PROGRESS.md` if it exists.
2. Inspect relevant files before editing.
3. Choose the highest-priority incomplete task from the backlog.
4. Write a short implementation plan in your own working notes.
5. Make the change.
6. Run the smallest relevant tests first, then the broader suite if feasible:
   - backend pytest
   - frontend unit tests
   - Playwright E2E when auth/progress/frontend flows change
7. Fix failures caused by your changes.
8. Update `RALPH_PROGRESS.md` with:
   - What you changed
   - Files touched
   - Tests run and results
   - Remaining gaps
   - Recommended next task
9. Commit the change with a clear commit message.
10. Stop after one coherent completed slice.

Definition of done for each loop:
- App still starts locally
- Relevant tests pass
- No secrets committed
- No hardcoded credentials introduced
- Data model changes are migration-safe
- User-facing behavior is preserved or intentionally improved
- `RALPH_PROGRESS.md` is updated
- Git commit created

When uncertain:
- Prefer the smallest safe implementation.
- Make assumptions explicit in `RALPH_PROGRESS.md`.
- Do not block waiting for human input unless continuing would risk data loss or major architecture churn.

First recommended task:
Start with P0-B if it is small and self-contained: secure config/secrets posture. Then proceed to P0-A auth, then P0-C persistence/migrations. Do not start progress dashboards until deployment safety is addressed.

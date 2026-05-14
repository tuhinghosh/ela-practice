# Ralph Loop Progress

Tracks each loop iteration against `docs/RALPH_BRIEF.md`. Newest first.

## Iteration 6 — P1-D: streak derived from activity history with explicit timezone

**Scope chosen.** First P1 item now that all P0 sub-items have meaningful
coverage. The brief asks for streak based on completed-activity dates (not
generic `updated_at`) with explicit timezone handling, plus tests for
same-day / consecutive / skipped / TZ cases. This is a self-contained
slice that strictly improves correctness with no new dependencies.

**Bug being fixed.** The old logic in `create_submission` derived streak
from the gap between `date.today()` (system local) and
`reward_state.updated_at` (UTC, updated on every write). Three problems:
(1) wrong source of truth — the update timestamp could refer to a stars
or badge change rather than the last *learning activity*; (2) silent
timezone mixing between system-local `today` and UTC `updated_at`; (3)
the row's `updated_at` is also set by initial reward-state seeding before
any activity exists, so the first submission could mis-count a same-day
"gap".

**Changes.**
- `backend/app/streak.py` (new) — pure `compute_streak(distinct_days_desc,
  today)` plus `get_distinct_learning_days(connection, child_id, tz)` and
  `compute_streak_for_child(connection, child_id, *, tz, today=None)`.
  Definition of a learning day: any calendar day, in the configured TZ,
  with at least one submitted session. Streak is alive if the latest
  learning day is today OR yesterday (so a child who studied yesterday
  still sees their streak today before doing today's lesson).
  `_parse_sqlite_utc_timestamp` handles both `'YYYY-MM-DD HH:MM:SS'` and
  ISO-8601 forms with `Z` or explicit offsets.
- `backend/app/config.py` — adds `Settings.learning_day_timezone`
  (`ZoneInfo`), parsed from `LEARNING_DAY_TIMEZONE` env var. Invalid
  zones fail fast at startup with `ConfigError`. Defaults to `UTC`.
- `backend/app/db.py` — `create_submission` now calls
  `compute_streak_for_child` against the child's full submission history
  (the just-inserted session is included), using the configured TZ. The
  ad-hoc `date.today() - last_updated` math is gone.
- `backend/tests/test_streak.py` (new) — 18 cases:
  - 7 pure-math cases: empty, today-only, yesterday-only, two-days-ago=0,
    five consecutive, gap breaks the run, yesterday-anchored history.
  - 3 timestamp parsing cases: default form, ISO with `Z`, ISO with
    `+05:30` offset.
  - DB-level: same-day submissions de-dup, three consecutive days→3,
    skipped middle day→2, UTC and US/Pacific each compute correctly for a
    timestamp that lives in the prior PT day vs same UTC day.
  - Integration: two real `create_submission` calls on the same day both
    return `streak_after=1`.
  - Config: default UTC, invalid zone raises `ConfigError`, valid IANA
    name accepted.
- `.env.example` — documents `LEARNING_DAY_TIMEZONE`.

**Tests run.**
- `python3 -m pytest backend/tests -q` → 122 passed (18 new in
  `test_streak.py`; all 104 from prior iterations still green). The
  existing `test_repeat_submissions_are_predictable` test in
  `test_api_routes.py` continues to pass because the new logic preserves
  the same-day-no-increment property.

**Assumptions / scope decisions.**
- One global timezone, not per-user. For a family MVP the parent picks
  the household's TZ via env; a per-user setting is overkill until
  multi-family arrives.
- Streak is recomputed from history on every submit (cheap — distinct
  dates over a child's full session history is a few-hundred-row scan at
  worst for an MVP). No need for an incremental cache beyond the
  `reward_state.streak_days` mirror that the dashboard already reads.
- The "alive yesterday" rule keeps streak visible until the day after
  it's broken — matches how Duolingo / Khan Academy and similar apps
  behave, and reduces false "you broke your streak" panic.

**Definition of done check.**
- App still starts locally: yes (no breaking API changes; the only
  observable shift is that streak values are now correct).
- Tests pass: 122/122.
- No secrets or hardcoded credentials introduced.
- Data model changes: none — the existing `streak_days` column in
  `reward_state` stays as the cached value; only the source it is
  computed from changed.
- User-facing behavior preserved for happy paths (same-day no-increment,
  consecutive-day +1); the fix is a correctness improvement, not a
  regression risk for normal usage.

**P1 status.** P1-D done. P1-E (improve progress tracking — per-skill
performance over time, 7/30/all-time windows, parent-facing "what to
practice next") still open.

**Recommended next task.** P1-E. Today the parent progress view shows
average-score / strengths / growth-areas but those snapshots are
single-point-in-time. The time-windowed summaries and a simple
"practice this next" pointer would meaningfully improve the parent UX
without needing AI involvement.

---

## Iteration 5 — P0-B (follow-up): CSRF Origin check on state-changing routes

**Scope chosen.** Closes the last open P0-B sub-item. Picked the
Origin/Referer approach over a double-submit cookie because: (a) browsers
always send `Origin` on cross-site POSTs so the signal is reliably
present, (b) it needs no frontend changes (the SPA already same-origins
the API in our deployment), (c) it needs no test-client changes
(non-browser clients omit `Origin` and pass through, because they cannot
ride a victim's session cookie anyway), and (d) it layers on top of the
existing `SameSite=Lax` cookie which already blocks most cross-site
POSTs.

**Changes.**
- `backend/app/csrf.py` (new) — `CSRFOriginMiddleware` (subclass of
  starlette `BaseHTTPMiddleware`). For unsafe methods (`POST`, `PUT`,
  `PATCH`, `DELETE`) targeting `/api/*`:
  - Safe methods short-circuit.
  - `/api/auth/login` is exempt (chicken-and-egg — no session yet).
  - If no `Origin` and no `Referer` is present, request is allowed
    (non-browser flow).
  - Otherwise the origin host (or referer host fallback) must equal the
    request's `Host` / URL netloc OR be in the configured allow list.
    Otherwise 403 with `{"error": "CSRF check failed", "detail": "..."}`.
- `backend/app/config.py` — adds `Settings.csrf_allowed_origins` parsed
  from `CSRF_ALLOWED_ORIGINS` (comma-separated). Empty default; the
  request's own host is always trusted implicitly.
- `backend/app/main.py` — installs `CSRFOriginMiddleware` outside
  `SessionMiddleware` so unauthorized cross-origin requests are rejected
  before session lookup even runs.
- `backend/tests/test_csrf.py` (new) — 14 cases via a small standalone
  FastAPI app for the unit path plus integration smoke against the real
  app:
  - no Origin → allowed; matching Origin → allowed; mismatched Origin →
    403; Referer fallback (matching and mismatching); GET ignores
    Origin; non-`/api/` paths ignored; `/api/auth/login` exempt;
    explicit allow list with full URL and bare host; malformed Origin →
    403; real-app `/api/auth/login` works cross-origin; real-app
    `/api/activities/.../submit` returns 403 with mismatched Origin;
    config parses + defaults to empty tuple.
- `.env.example` — documents `CSRF_ALLOWED_ORIGINS`.
- `docs/DEPLOYMENT.md` — new "CSRF" section explains the model and the
  `CSRF_ALLOWED_ORIGINS` knob.

**Tests run.**
- `python3 -m pytest backend/tests -q` → 104 passed (14 new in
  `test_csrf.py`; all 90 from prior iterations still green).

**Assumptions / scope decisions.**
- Login is exempt by design. The realistic attack on login CSRF is "make
  the victim sign in as the attacker", which would deliver the attacker's
  data into the victim's hands but not vice versa, and doesn't apply to
  a single-account family app today. Brute-force is covered by hashed
  passwords + per-IP rate limiting (iter 2 and iter 4).
- We do not implement double-submit cookie / synchronizer token because
  the SameSite=Lax + Origin combination is sufficient for the threat
  model and avoids both frontend and test churn.
- Tests that omit `Origin` continue to pass — they pre-date this
  iteration and exercise the request layer in a non-browser way. They
  remain valid because the omitted-`Origin` branch is documented
  behavior, not a workaround.

**Definition of done check.**
- App still starts locally: yes (no breaking behavior change for
  same-origin requests).
- Tests pass: 104/104.
- No secrets or hardcoded credentials introduced.
- No data model changes.
- User-facing behavior preserved (the SPA POSTs same-origin → still 200).

**P0 status.** All P0 items now have meaningful coverage:
- P0-A: hashed-credential login, role column, env-bootstrap (iter 2).
- P0-B: SESSION_SECRET hygiene + cookies (iter 1), rate limit (iter 4),
  CSRF (iter 5).
- P0-C: versioned migrations + online backup + deployment doc (iter 3).

Remaining P0 polish (not blocking): in-app user management UI, child-role
accounts, formal threat-model review. These move to P1/P2 priority.

**Recommended next task.** P1-D streak logic. Today the streak count
piggy-backs on `reward_state.updated_at`, which is the wrong source of
truth — it ticks on every submission update regardless of the activity
date and gets confused by same-day vs consecutive-day boundaries.
Replace with a proper streak derived from distinct activity dates with
explicit timezone handling.

---

## Iteration 4 — P0-B (follow-up): per-IP login rate limiting

**Scope chosen.** P0-B's outstanding sub-items are CSRF and login rate
limiting. Rate limiting is the smaller, more contained slice and directly
reduces the brute-force surface that the new hashed-credential login from
iter 2 created — picking it first follows the brief's "smallest safe
implementation" rule. CSRF stays deferred to a later iteration.

**Changes.**
- `backend/app/rate_limit.py` (new) — `SlidingWindowLimiter` with a per-key
  deque of failure timestamps. `check(key)` is the gate (prune, then block
  if `len(bucket) >= max_attempts`); `register_failure(key)` records one
  attempt without returning allow/deny so the endpoint logic stays a
  single check-at-entry. `clear(key)` releases a key on successful login
  so a fat-fingering user does not get locked out. Time source injectable
  for tests. Thread-safe via `threading.Lock` (sync FastAPI handlers can
  run in the threadpool).
- `backend/app/config.py` — adds `login_rate_limit_max_attempts` (default
  10) and `login_rate_limit_window_seconds` (default 60). Setting either
  to `0` disables the limiter. New `_parse_non_negative_int` helper
  validates ints; rejects non-numeric and negative values with `ConfigError`.
- `backend/app/main.py` — module-level `login_limiter` constructed from
  settings at import. `/api/auth/login` keys on `request.client.host`:
  - `check()` at entry → 429 + `Retry-After` if blocked.
  - On 401 path (unknown user OR wrong password), `register_failure()`.
  - On 200 path, `login_limiter.clear(key)`.
  - Constant-time-ish: the credential check still runs to completion on
    failure (no early exit on unknown user changes timing meaningfully
    here because the limiter triggers before timing differences matter).
- `backend/tests/conftest.py` — adds `reset_login_limiter` autouse fixture
  so the module-level limiter's state does not leak across tests.
- `backend/tests/test_rate_limit.py` (new) — 15 cases:
  - unit: accumulate-then-block, check is non-recording, clear releases,
    window expiry releases (via injected clock), separate keys
    independent, `max_attempts=0` and `window_seconds=0` both disable,
    negative ctor args rejected
  - config: env vars parsed, defaults set, non-integer rejected, negative
    rejected
  - integration via TestClient: 11th request returns 429 + `Retry-After`,
    successful login resets the budget, conftest reset works between tests
- `.env.example` — documents the two new env vars (commented; defaults
  shown).

**Tests run.**
- `python3 -m pytest backend/tests -q` → 90 passed (15 new in
  `test_rate_limit.py`; all 75 from prior iterations still green).

**Assumptions / scope decisions.**
- Per-IP only, not per-(IP,username). For a home server behind one IP
  this is enough; per-username would lock out legitimate users when an
  attacker probes a known account, and per-pair lets an attacker enumerate
  users without ever hitting any single pair's cap. Per-IP is the safest
  default at this scale; revisit if the app is ever exposed behind a CDN
  or shared NAT.
- State is in-process and lives in memory: it does not survive process
  restart and is not shared across uvicorn workers. Acceptable for the
  single-container MVP; documented in the module docstring.
- The limiter never returns `allowed=False` from `register_failure` — the
  endpoint gates only on `check()`. This avoids the off-by-one trap where
  the "Nth attempt that just got recorded" both gets a 401 reply AND
  flips the bucket to blocked, surfacing as a confusing 429 on the same
  request the user just made.

**Definition of done check.**
- App still starts locally: yes (login limiter constructed lazily from
  settings; no behavior change unless config is set).
- Tests pass: 90/90.
- No secrets or hardcoded credentials introduced.
- No data model changes.
- User-facing behavior preserved: 401 still returned on bad creds; 429
  is only added under sustained abuse from one IP.

**P0 status.** Of P0-B, only CSRF remains. P0-A and P0-C are
structurally complete.

**Recommended next task.** P0-B CSRF protection for state-changing
routes. After that, P1-D (streak logic fix) and P1-E (progress tracking)
since P0 will be done.

---

## Iteration 3 — P0-C: versioned migrations + online backup + deployment doc

**Scope chosen.** P0-C is the last P0 item: persistent SQLite with
migrations and backups. This iteration ships the structural pieces
(versioned migration runner, online backup helper + script, deployment
docs) so future schema changes have a single, testable code path and ops
has a documented backup story. `DATABASE_PATH` was already configurable
(verified) and the existing start scripts already mount a Docker volume —
we now document both.

**Changes.**
- `backend/app/migrations.py` (new) — versioned, append-only runner.
  `Migration(id, name, apply)` entries live in `MIGRATIONS`; `run_migrations`
  applies any whose ids are missing from the `schema_migrations` table and
  records them. Migration 1 (`add_user_auth_columns`) wraps the column-add
  logic introduced in iteration 2; it is idempotent via column-presence
  checks so DBs already migrated by iter 2's ad-hoc code path converge
  cleanly when iter 3 ships.
- `backend/app/db.py` — `ensure_database()` now calls `run_migrations()`
  instead of the prior `apply_migrations()`; the inline function is gone.
- `backend/app/backup.py` (new) — `backup_database(target, source=None,
  overwrite=False)` using `sqlite3.Connection.backup` (safe under concurrent
  writes). Module is also CLI-invokable:
  `python3 -m backend.app.backup <target> [--source PATH] [--overwrite]`.
- `scripts/backup-db.sh` (new, executable) — thin wrapper that defaults
  target to `backups/ela-<UTC>.sqlite3` and shells out to the Python module.
  Smoke-tested end-to-end against a freshly seeded DB; copy is byte-for-byte
  identical and identifies as `SQLite 3.x database` via `file`.
- `docs/DEPLOYMENT.md` (new) — covers DB location + `DATABASE_PATH`
  override, Docker volume mount (with example `docker run`), migration
  policy (append-only, never edit shipped migrations), backup usage,
  restore procedure, and an example cron entry.
- `backend/tests/test_migrations.py` (new) — 4 cases: fresh schema records
  all migration ids; rerun is a no-op (returns empty list); legacy-schema
  DB (pre-iter-2 shape) is brought up to date; full smoke test from
  non-existent file to usable seeded DB with `schema_migrations` populated.
- `backend/tests/test_backup.py` (new) — 5 cases: backup produces readable
  copy preserving seed + custom row; refuses overwrite by default; honors
  `overwrite=True` (including when target previously held non-SQLite
  bytes); rejects missing source; rejects same source/target path.

**Tests run.**
- `python3 -m pytest backend/tests -q` → 75 passed (9 new this iteration,
  all 66 prior still green).
- Manual CLI smoke: `python3 -m backend.app.backup` and
  `scripts/backup-db.sh` both write a valid SQLite file.

**Assumptions / scope decisions.**
- Migrations are append-only; future schema work writes new
  `Migration(id=N+1, ...)` entries rather than editing prior ones. Tests
  assert the contract by iterating over `MIGRATIONS`.
- A versioned migration runner is overkill for a family MVP today but is
  the smallest change that lets P1 (per-skill history schema changes,
  child-role accounts, etc.) ship without ad-hoc ALTERs scattered through
  `db.py`.
- The shell script depends on `python3` being on PATH; intentional — the
  app already requires Python at runtime, and using the sqlite3 binary
  would mean two divergent backup code paths.

**Definition of done check.**
- App still starts locally: yes (no behavior changes; `ensure_database`
  contract unchanged, migration runner is a no-op on already-migrated DBs).
- Tests pass: 75/75.
- No secrets committed.
- No hardcoded credentials introduced.
- Data model changes are migration-safe (this iteration's whole point).
- User-facing behavior preserved.
- `ralph_progress.md` updated; commit forthcoming.

**P0 status.** With this iteration, the P0 deployment-safety foundation
is structurally complete: env-driven config + secret guard (iter 1),
hashed-credential login + role column + tenant isolation (iter 2),
versioned migrations + online backup + deployment doc (iter 3).
Remaining P0-B sub-items still open: CSRF for state-changing routes and
login rate limiting.

**Recommended next task.** P0-B follow-up: login rate limiting. It is
small, self-contained (one endpoint), and reduces the risk surface of the
new credential lookup. After that, CSRF for state-changing routes. Then
move to P1 (streak logic + progress tracking).

---

## Iteration 2 — P0-A (partial): password hashing, role column, bootstrap from env

**Scope chosen.** P0-A asked for real local user management. This iteration
takes the vertical slice that removes the literal `user/password` compare and
introduces persistent hashed credentials with a `role` column, while keeping
the dev workflow (and all existing tests) running unchanged. Deferred:
in-app account creation UI, separate child-login accounts, and CSRF/rate
limit work (P0-B remainder).

**Changes.**
- `backend/app/auth.py` (new) — `hash_password` / `verify_password` using
  `hashlib.pbkdf2_hmac` (sha256, 240k iterations). Stdlib-only so no new
  dependency. Encoded as `pbkdf2_sha256$iter$salt$hash`. Verify is
  constant-time and returns `False` on unparseable input.
- `backend/app/db.py` — `users` table gains `password_hash TEXT` and
  `role TEXT NOT NULL DEFAULT 'parent' CHECK(role IN ('parent','child'))`.
  New `apply_migrations()` runs additive `ALTER TABLE` for legacy DBs so
  existing on-disk databases pick up the columns on next start without data
  loss. `seed_core_records()` now reads bootstrap creds from settings, hashes
  them, and backfills `password_hash` for any pre-existing seed user with a
  `NULL` hash. `get_user_by_username` returns the hash + role.
- `backend/app/config.py` — `Settings` gains `bootstrap_username` and
  `bootstrap_password`. In prod both are required and the password may not
  equal the dev placeholder; in dev defaults to `user`/`password` so existing
  fixtures continue to log in.
- `backend/app/main.py` — `/api/auth/login` now looks up the user, verifies
  the hash with `verify_password`, and stores `username` + `role` in the
  session. `/api/auth/session` returns `role` alongside `username` (null
  when unauthenticated).
- `backend/tests/conftest.py` (new) — autouse fixture redirects
  `DATABASE_PATH` to a per-test tmp file and calls `ensure_database()`, so
  every test runs against a fresh, migrated, seeded DB. Required because
  several tests bypass FastAPI lifespan via `ASGITransport` and previously
  used the shared on-disk dev DB.
- `backend/tests/test_user_management.py` (new) — 15 cases:
  - hash round-trip, salt uniqueness, wrong-password rejection, bad-format
    handling
  - login success with seeded creds, wrong password, unknown user, session
    endpoint role field (authed + unauthed)
  - prod requires `ELA_BOOTSTRAP_USERNAME`, requires `ELA_BOOTSTRAP_PASSWORD`,
    rejects dev placeholder password, accepts real creds; dev defaults
    resolve to `user`/`password`
  - tenant isolation: a second seeded parent cannot read the first parent's
    session via `/api/sessions/{id}` (returns 404)
- `backend/tests/test_config.py` — updated prod-mode cases to include
  bootstrap creds since they are now required for prod settings to load.
- `.env.example` — documents `ELA_BOOTSTRAP_USERNAME`,
  `ELA_BOOTSTRAP_PASSWORD`, and `DATABASE_PATH`.

**Tests run.**
- `python3 -m pytest backend/tests -q` → 66 passed (15 new in
  `test_user_management.py`, plus all 51 from iteration 1 still green). No
  frontend tests run — frontend was not touched.

**Assumptions / scope decisions.**
- Children currently do not log in directly; the seeded parent account owns
  the single child profile (matching today's UX). Adding child-role users is
  a follow-up that requires UI and per-role authorization on routes.
- Existing on-disk databases (e.g. a developer's `backend/data/ela.sqlite3`)
  pick up the new columns via `apply_migrations()` on next start; the
  existing seed user gets its hash backfilled. No data loss.
- PBKDF2 is acceptable for an MVP without adding a new dependency; bcrypt or
  argon2 are stronger choices for a public deployment and should be
  revisited if/when this leaves family use.

**Remaining gaps in P0-A.**
- No in-app password change or account-creation flow.
- No separate child-role users; child role exists only as a column constraint
  today.
- No tenant isolation enforcement beyond session ownership checks already in
  routes — added a regression test, did not add a sweep of all routes.

**Remaining gaps in P0-B (deferred from iteration 1).**
- CSRF protection for state-changing routes.
- Login rate limiting.

**Recommended next task.** P0-C (persistent SQLite + migrations) is the last
P0 item. The migration scaffold added here (`apply_migrations`) is a
natural foundation: extend it into a versioned migration runner, document
the Docker volume in `start-mac.sh` / `docker-compose`, and add a backup
command. After P0-C the deployment safety foundation is complete and we
can move to P1.

---

## Iteration 1 — P0-B (partial): SESSION_SECRET hygiene + cookie config + .env.example

**Scope chosen.** P0-B is the largest backlog item; this iteration takes the
smallest tightly-coupled slice (secret/cookie config + sample env file +
tests) and defers CSRF and login rate-limiting to later iterations so each
slice stays reviewable.

**Changes.**
- `backend/app/config.py` (new) — `Settings` dataclass + `load_settings()`
  that reads `ELA_ENV`, `SESSION_SECRET`, `SESSION_COOKIE_NAME`,
  `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`. Validation:
  - `ELA_ENV=prod` requires a non-empty `SESSION_SECRET` that is not the dev
    placeholder.
  - `ELA_ENV=dev` falls back to the existing dev placeholder and logs a
    warning so it is visible in startup logs (preserves test/dev behavior).
  - Cookie defaults: in prod, `secure=True`; in dev, `secure=False`. Both
    overridable. `samesite=none` requires `secure=true`.
- `backend/app/main.py` — replaced inline `os.environ` reads with
  `get_settings()`; cookie flags now come from settings.
- `backend/tests/test_config.py` (new) — 10 cases covering dev default with
  warning, dev explicit secret without warning, prod missing secret, prod
  rejecting dev placeholder, prod cookie defaults, cookie override, samesite
  none + insecure rejected, invalid env name, invalid boolean, custom cookie
  name.
- `.env.example` (new) — documents `ELA_ENV`, `SESSION_SECRET`,
  `SESSION_COOKIE_*`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` with safe
  placeholders. Includes a one-liner for generating a strong secret.

**Tests run.**
- `python3 -m pytest backend/tests -q` → 51 passed (10 new in `test_config`,
  41 existing). Frontend tests not run; no frontend code touched.

**Assumptions.**
- `.gitignore` already covers `.env` (line 130) and does not cover
  `.env.example`; confirmed via `git check-ignore`.
- Existing tests rely on dev-mode default behavior (no env vars set); the
  config module preserves that path so no test fixture changes were needed.

**Remaining gaps in P0-B.**
- CSRF protection for state-changing routes.
- Login rate limiting.
- Server-only OpenRouter key handling beyond current state (it is already
  only read in the backend; no frontend exposure to remove).

**Recommended next task.** P0-A (real local user management with hashed
passwords and parent/child roles). It is the highest-priority remaining
P0 item and is a prerequisite for proper tenant isolation tests that will
also strengthen the auth surface for the CSRF/rate-limit work.

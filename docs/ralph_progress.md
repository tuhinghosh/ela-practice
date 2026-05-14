# Ralph Loop Progress

Tracks each loop iteration against `docs/RALPH_BRIEF.md`. Newest first.

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

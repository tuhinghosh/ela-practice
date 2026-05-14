# Deployment

ELA is designed to run as a single Docker container on a home/personal
server. This doc covers the bits that aren't obvious from `README` or
`CLAUDE.md`: where data lives, how schema changes are applied, and how to
back up the database.

## Database location

The SQLite database is the single source of truth for accounts, sessions,
scores, and rewards. By default it lives at:

```
backend/data/ela.sqlite3
```

Override with the `DATABASE_PATH` environment variable. The path must be
writable by the running process.

### Docker volume

`scripts/start-mac.sh` (and the Linux/Windows counterparts) mount
`./backend/data` from the host into the container at
`/app/backend/data`. That means the SQLite file outlives container
rebuilds and is included in any host-level backups.

If you run the image yourself, mount a host directory (or named volume)
at `/app/backend/data`, e.g.:

```bash
docker run -d \
  --name ela-mvp \
  --env-file .env \
  -p 8000:8000 \
  -v /var/lib/ela/data:/app/backend/data \
  ela-mvp
```

Without a volume mount, every container rebuild wipes user accounts and
progress. Don't skip this.

## Migrations

Schema changes are managed by `backend/app/migrations.py`. On every app
start (and on every test via `conftest.py`), `ensure_database()`:

1. Runs `CREATE TABLE IF NOT EXISTS` for the base schema in
   `db.py:create_schema`.
2. Runs `run_migrations()` which applies any migrations whose ids are not
   recorded in the `schema_migrations` table, then records them.
3. Seeds the bootstrap parent account from `ELA_BOOTSTRAP_USERNAME` /
   `ELA_BOOTSTRAP_PASSWORD` (or the dev defaults).

Migrations are append-only and idempotent. To add one: write a function
that takes a `sqlite3.Connection`, give it the next sequential id, and
append a `Migration(...)` entry to `MIGRATIONS`. Never edit a shipped
migration — write a new one.

## Backups

Use the included script — it calls SQLite's online backup API, which is
safe to run while the app is serving traffic:

```bash
scripts/backup-db.sh                                  # → backups/ela-<UTC>.sqlite3
scripts/backup-db.sh /var/backups/ela-snapshot.db     # → custom path
```

Or invoke the Python module directly:

```bash
python3 -m backend.app.backup /tmp/ela-snapshot.sqlite3
python3 -m backend.app.backup --overwrite /tmp/ela-snapshot.sqlite3
```

`DATABASE_PATH` is read for the source when `--source` is not provided.

### Restoring

The backup file is a complete SQLite database. To restore: stop the app,
replace `backend/data/ela.sqlite3` with the backup file (keeping the
filename), and start the app. The migration runner will re-record any
schema migrations already present.

### Scheduling

There is no built-in scheduler. For a home server, the simplest setup is
a host cron entry:

```cron
# Daily backup at 03:15 local time
15 3 * * * /path/to/repo/scripts/backup-db.sh >> /var/log/ela-backup.log 2>&1
```

Prune old backups with your tool of choice (e.g. `find ... -mtime +30 -delete`).

## CSRF

State-changing requests to `/api/*` (POST/PUT/PATCH/DELETE) are guarded by
an Origin/Referer check. Browsers always send `Origin` on cross-site
POSTs, so a malicious page that tries to ride the user's session cookie
will be blocked with a 403. `/api/auth/login` is exempt — login has no
prior session, and brute-force is mitigated by hash verification plus
per-IP rate limiting.

The request's own `Host` is always trusted. If you serve the SPA from a
different origin than the API (e.g. `app.example.com` calling
`api.example.com`), list the SPA origin via `CSRF_ALLOWED_ORIGINS`:

```
CSRF_ALLOWED_ORIGINS=https://app.example.com,https://parents.example.com
```

Non-browser clients (curl, scripts, the test suite) that omit `Origin`
pass through, because they cannot ride a victim's session cookie.

## Observability

### Health checks

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /api/health` | Liveness — process is up | always `200` |
| `GET /api/ready`  | Readiness — DB reachable + migrated | `200` ok, `503` if DB error |

Wire these into your process supervisor or load balancer accordingly.

### Logging

All app logs are emitted as one JSON object per line on **stderr**. Each
record contains at minimum `timestamp` (UTC ISO-8601), `level`, `logger`,
and `message`. Structured fields (e.g. `request_id`, `duration_ms`,
`model`) appear as top-level keys for easy filtering.

Per-request logs come from logger `ela.request` with `event=http_request`
and include `method`, `path`, `status_code`, `duration_ms`, `client_ip`.
**Request bodies are never logged** — child free-text answers must stay
out of operator-facing telemetry.

AI calls come from logger `ela.ai_call` with `event=ai_call`. Each entry
includes `provider`, `model`, `duration_ms`, `status` (`ok` / `error`),
`error_class` (when applicable), and OpenRouter usage tokens when the
provider returns them. **Prompts and responses are never logged.**

Set the log level via `LOG_LEVEL` (default `INFO`).

### AI call cap

`AI_CALLS_PER_USER_PER_DAY` (default `50`) caps OpenRouter calls per
authenticated user per UTC day across `/api/ai/coach` and
`/api/ai/connectivity-check`. The 51st call returns `429 Too Many
Requests` with a `reset_at` timestamp in the body. Set to `0` to
disable. The counter is in-memory and resets on process restart — fine
for a single-container deployment; revisit if scaling out.

## Rotating the parent password

The bootstrap credential set via `ELA_BOOTSTRAP_USERNAME` /
`ELA_BOOTSTRAP_PASSWORD` is only used the very first time the app sees
an empty database — once `users.password_hash` exists, changing the env
var does **not** update the stored row.

Rotate the password from the running app:

1. Sign in as the parent.
2. Open `/parent/progress` and use the "Account password" card.
3. Enter the current password and a new one (at least 8 characters);
   the form posts to `POST /api/auth/password`.

The endpoint is CSRF-guarded, requires an authenticated session, and
shares the per-IP login rate limiter — too many wrong current-password
attempts will return `429 Too Many Requests`. There is no out-of-band
recovery path: lose both the current password and direct DB access and
you'll have to drop the user row and let the bootstrap re-seed.

## Content workflow

The canonical activity / theme / skill-tag data lives in
`backend/content/`. The Docker image picks it up via the regular
`COPY backend/` step — no cross-tree copy is needed.

`backend/content/MANIFEST.json` records `content_version` and a SHA256
for every canonical file. The app validates the manifest on startup via
`verify_content_manifest()`; the test suite re-runs the full schema /
cue checks on every commit.

The Next.js bundle still imports the JSON at compile time, so
`frontend/src/content/` carries a synced mirror of the same files. The
test `test_frontend_mirror_matches_backend_canonical` fails on drift.

CLI:

```bash
# Re-run schema + cue checks and verify manifest checksums.
python3 -m backend.app.content_cli validate

# Recompute checksums and rewrite MANIFEST.json (run after editing).
python3 -m backend.app.content_cli manifest

# Copy canonical files to frontend/src/content (run after manifest).
python3 -m backend.app.content_cli sync

# Wrapper that runs validate + sync end-to-end.
scripts/sync-content.sh
```

When editing activities, the workflow is: edit a file under
`backend/content/`, run `scripts/sync-content.sh`, commit both the
canonical edit and the regenerated mirror.

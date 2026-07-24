# Deployment

ELA is designed to run as a single Docker container on a home/personal
server. This doc covers the bits that aren't obvious from `README` or
`CLAUDE.md`: where data lives, how schema changes are applied, and how to
back up the database.

The verified Reyana private-pilot deployment has a separate practical
operator guide in [`RAILWAY_RUNBOOK.md`](RAILWAY_RUNBOOK.md).

## Deploying to Railway

End-to-end recipe. Skip ahead to the "Behind a reverse proxy" section
below for the env var that makes the rate limiter work correctly once
you're up.

### 1. Connect the repo

In Railway: **New Project → Deploy from GitHub repo → pick this repo**.
Railway detects `Dockerfile` automatically and reads `railway.toml`
from the repo root for healthcheck + restart settings. No build
command override needed.

### 2. Attach a persistent volume

**This is required.** Without it, every redeploy wipes user accounts,
sessions, scores, rewards, and AI call history.

In the Railway service settings:

- Volumes → **New Volume** → mount path `/app/backend/data` → size
  `1 GB` (plenty for an MVP; the SQLite DB is hundreds of KB even with
  years of data).

The Docker image runs as root inside the container so it can write to
the Railway-mounted volume on first start. The platform sandbox is the
security boundary, not the in-container UID.

### 3. Set environment variables

In the service's **Variables** tab, set at minimum:

| Variable | Value | Why |
|----------|-------|-----|
| `ELA_ENV` | `prod` | Enables strict secret validation + `Secure` cookies. |
| `SESSION_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` | Required in prod; rejects the dev placeholder. |
| `ELA_BOOTSTRAP_USERNAME` | (your choice, e.g. `parent`) | Seeded on first start only. |
| `ELA_BOOTSTRAP_PASSWORD` | (strong password, 8+ chars) | Required in prod; rejected if it matches the dev placeholder. |
| `OPENROUTER_API_KEY` | (your key) | Empty means AI coach features fail closed. |
| `TRUSTED_PROXY_IPS` | `*` | **Required** behind Railway — without it the per-IP rate limiter collapses (see below). |

Optional but recommended:

| Variable | Sensible value | Why |
|----------|---------------|-----|
| `LEARNING_DAY_TIMEZONE` | your local IANA zone, e.g. `America/Los_Angeles` | Streak day boundaries match the child's experience. |
| `AI_CALLS_PER_USER_PER_DAY` | `50` (default) | Cost cap. Lower for tighter spend control. |
| `LOG_LEVEL` | `INFO` (default) | `DEBUG` for troubleshooting. |

After saving variables, Railway will redeploy. Watch the logs for
`migrations_applied=...` in the `/api/ready` probe — that means schema
migrations ran cleanly.

### 4. Verify

- `curl https://<your-service>.up.railway.app/api/health` → `{"status":"ok"}`
- `curl https://<your-service>.up.railway.app/api/ready` → `{"status":"ok","migrations_applied":3}`
- Visit `https://<your-service>.up.railway.app/login` and sign in
  with the bootstrap credentials. **Immediately rotate the password**
  via `/parent/progress` → "Account password".

### 5. Caveats

- **Cron is not built in.** The AI call log pruner
  (`python3 -m backend.app.ai_quota_prune`) and backup script
  (`scripts/backup-db.sh`) assume a host cron. On Railway you'd need
  to add a Railway Cron service (separate cron worker) pointing at the
  same volume — or accept the unbounded `ai_call_log` table for the
  MVP's lifetime (~18k rows/year at the default cap, still well
  within SQLite's comfort zone).
- **Backups live on the same volume.** A volume corruption loses both
  the DB and the backups. For real production hygiene, periodically
  download a backup with `railway run scripts/backup-db.sh` and store
  it off-platform.
- **Single worker.** The default uvicorn process serves one worker.
  The in-memory `login_limiter` and the SQLite WAL don't tolerate
  multi-worker scale-out as written. Family-MVP scale is fine on one.
- **Outbound network**: the only outbound dependency is
  `api.openrouter.ai:443`. Allowed by default on Railway.

## Behind a reverse proxy (Railway, Fly, nginx, Cloudflare)

If anything terminates TLS in front of the container — Railway, Fly,
an nginx in front, Cloudflare, etc. — the container sees every request
as coming from the proxy's IP. That breaks the per-IP login rate
limiter (everyone shares one bucket; 10 wrong attempts from anyone
locks out everyone). Set:

```
TRUSTED_PROXY_IPS=*
```

The app installs uvicorn's `ProxyHeadersMiddleware` as the outermost
layer; with the trust set, it rewrites `request.client.host` from
`X-Forwarded-For` so the rate limiter sees real client IPs again.

**Only use `*` when the operator controls every network path to the
container** (Railway, Fly: yes — direct internet access is blocked by
the platform). When the container is reachable directly from the
internet, narrow the value to specific proxy IPs or leave it unset.

Leaving `TRUSTED_PROXY_IPS` empty (the default) means the middleware
is installed but never rewrites — identical to having no proxy
middleware at all. Home-server installs without a proxy in front
should keep it empty.

---


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

### Pruning old backups

`scripts/prune-backups.sh` (defaults: `backups/`, keep 30) deletes the
oldest files by mtime in a backup directory so the disk does not fill
up:

```bash
scripts/prune-backups.sh                                    # backups/, keep 30
scripts/prune-backups.sh /var/backups/ela --keep 14         # custom dir, keep 14
python3 -m backend.app.backup_prune backups/ --keep 30      # direct CLI
```

The script prints a one-line summary with the deletion count and
remaining count for log scraping. Example crontab pairing backup +
prune:

```cron
# Daily backup at 03:15, prune to last 30 at 03:30.
15 3 * * * /path/to/repo/scripts/backup-db.sh    >> /var/log/ela-backup.log 2>&1
30 3 * * * /path/to/repo/scripts/prune-backups.sh >> /var/log/ela-backup.log 2>&1
```

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
disable.

The counter is persisted in the SQLite ``ai_call_log`` table, so the
cap survives container rebuilds.

### Pruning the AI call log

`AI_CALL_LOG_RETENTION_DAYS` (default `90`) sets how long rows live.
Run the pruner from cron to keep the table from growing forever:

```bash
python3 -m backend.app.ai_quota_prune              # uses retention from env
python3 -m backend.app.ai_quota_prune --days 30    # one-off override
```

Set the env var to `0` to disable pruning entirely. The pruner prints
the deletion count on a single line for log scraping. Example crontab
on a single-container host:

```cron
# Prune the AI call log nightly at 02:30.
30 2 * * * /path/to/repo && python3 -m backend.app.ai_quota_prune >> /var/log/ela-prune.log 2>&1
```

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

### Hot reload (no restart)

After editing canonical content on a running instance, you can pick up
the change without bouncing the container:

```bash
curl -X POST -b cookies.txt -c cookies.txt http://localhost:8000/api/admin/content/reload
```

The endpoint requires an authenticated parent session, clears the cached
activity list, re-verifies `MANIFEST.json`, and re-runs the full
validator. The response includes the new `activity_count`,
`theme_count`, and `content_version`. A manifest mismatch returns 500
with the offending file in `detail` — re-run `content_cli manifest` and
try again.

The frontend bundle still has a compile-time copy of the JSON, so a
front-end refresh is needed to pick up edits there — that means a
re-`build` of the static export, or a `scripts/sync-content.sh` + dev
server reload for local edits.

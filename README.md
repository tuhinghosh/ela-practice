# ELA Reading and Writing Adventure (MVP)

Local Docker-first MVP for a third-grade reading and writing practice app.

## Quick start

### macOS

```bash
./scripts/start-mac.sh
```

### Linux

```bash
./scripts/start-linux.sh
```

### Windows (PowerShell)

```powershell
./scripts/start-windows.ps1
```

App URL: `http://localhost:8000`

Login: `user` / `password` — this is the **dev bootstrap credential**.
The password is hashed at first run; rotate it from the parent progress
page ("Account password" card) before sharing the app with anyone.

## Stop

### macOS

```bash
./scripts/stop-mac.sh
```

### Linux

```bash
./scripts/stop-linux.sh
```

### Windows (PowerShell)

```powershell
./scripts/stop-windows.ps1
```

## Security posture

This is a family MVP, not a public SaaS — the goal is "safe private
deployment", not "internet-facing fortress". Layered defenses today:

- **Hashed credentials** (PBKDF2-HMAC-SHA256, stdlib). Bootstrap user is
  seeded from `ELA_BOOTSTRAP_USERNAME` / `ELA_BOOTSTRAP_PASSWORD`;
  in-app rotation via `/parent/progress`.
- **Session cookies** with `SameSite=Lax` by default, `Secure` on in
  prod, configurable via env. `SESSION_SECRET` is required in
  `ELA_ENV=prod` and the app fails fast if missing.
- **CSRF**: Origin/Referer check on state-changing `/api/*` requests
  (login exempt for the chicken-and-egg case). Cross-site POSTs from a
  malicious page get a 403.
- **Login rate limit**: per-IP sliding window, 10 failures / 60s by
  default. The password-change endpoint shares the same budget.
- **AI call quota**: per-user, per-UTC-day cap on OpenRouter calls
  (default 50), persisted in SQLite so it survives restarts. Returns
  429 with a `reset_at` timestamp.
- **Structured JSON logs** on stderr. Request bodies, AI prompts, and
  AI responses are never logged.
- **Migrations** are versioned and additive; **backups** via
  `scripts/backup-db.sh`.

Configurable knobs are in [`.env.example`](.env.example). Detailed
operator docs are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), which
covers cookie + CSRF + AI quota + content workflow + readiness probes.

## Persistence

- SQLite data is stored in `backend/data/ela.sqlite3`
- Start scripts mount `backend/data` into the container so data survives container restarts

## Test commands

Backend:

```bash
python3 -m pytest backend/tests -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm run test:unit
npm run test:e2e
```

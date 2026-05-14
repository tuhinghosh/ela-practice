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

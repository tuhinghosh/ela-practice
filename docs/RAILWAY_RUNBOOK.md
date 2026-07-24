# Railway private pilot runbook

This is the operating guide for Reyana's private family pilot. It records
resource names and safe commands, but never secret values or passwords.

## Live deployment

| Item | Value |
|------|-------|
| Application | https://ela-web-production.up.railway.app |
| Railway project | `reyana-reading-pilot` |
| Railway environment | `production` |
| Railway service | `ela-web` |
| Source | GitHub `main` |
| Region | San Francisco (`sfo`) |
| Health check | `/api/ready` |
| Volume | `ela-web-volume` |
| Volume mount | `/app/backend/data` |
| SQLite path | `/app/backend/data/ela.sqlite3` |

The URL is public so a normal browser can reach it. Application content and
progress are protected by the app's signed-in parent account. Do not share the
URL or credentials publicly.

## Deployment path

1. Changes are developed on a short-lived Git branch.
2. A pull request targets `main`.
3. GitHub runs backend tests, frontend tests, and the production Docker smoke
   harness.
4. The pull request is squash-merged only after all checks pass.
5. Railway detects the new `main` commit, builds the root `Dockerfile`, mounts
   the persistent volume, and waits for `/api/ready` to return HTTP 200.
6. The new deployment becomes active after the health check succeeds.

Because the service uses a Railway volume, a redeploy can have brief downtime.
Do not scale the service beyond one replica while it uses SQLite.

## Production variables

The service should have these operator-managed variables:

- `ELA_ENV=prod`
- `SESSION_SECRET` — generated secret; never display or commit it
- `ELA_BOOTSTRAP_USERNAME=parent`
- `ELA_BOOTSTRAP_PASSWORD` — first-database seed only
- `OPENROUTER_API_KEY` — server-side only
- `AI_CALLS_PER_USER_PER_DAY=10`
- `AI_CALL_LOG_RETENTION_DAYS=90`
- `LEARNING_DAY_TIMEZONE=America/Los_Angeles`
- `LOG_LEVEL=INFO`
- `TRUSTED_PROXY_IPS=*`

Railway also injects its own `RAILWAY_*` variables.

Changing `ELA_BOOTSTRAP_PASSWORD` after the account has been created does not
change the stored password. Rotate the current password from the parent
progress page instead.

## Routine checks

Run commands from the repository root after authenticating the Railway CLI.

```bash
railway whoami
railway status
railway volume list
```

Public liveness and readiness:

```bash
curl -fsS https://ela-web-production.up.railway.app/api/health
curl -fsS https://ela-web-production.up.railway.app/api/ready
```

Recent application logs:

```bash
railway logs --service ela-web --lines 100
```

Recent errors only:

```bash
railway logs \
  --service ela-web \
  --lines 100 \
  --filter "@level:error"
```

The app emits request metadata but not request bodies, AI prompts, AI
responses, or child-written answers.

## Restart and redeploy

Restart the active container without rebuilding:

```bash
railway restart --service ela-web --yes
```

Redeploy the current source revision:

```bash
railway redeploy --service ela-web --yes
```

After either operation, verify `/api/ready` and refresh an already signed-in
browser session. The session and learner data should survive because the
session secret is stable and SQLite is on the mounted volume.

## First response to a problem

1. Check `https://ela-web-production.up.railway.app/api/ready`.
2. Run `railway status`.
3. Read the latest bounded logs:

   ```bash
   railway logs --service ela-web --latest --lines 150
   ```

4. Confirm `ela-web-volume` is still mounted at `/app/backend/data`.
5. If the latest deployment is unhealthy, inspect its build and deployment
   logs before restarting or redeploying.
6. Do not delete the service, volume, environment, or project while diagnosing
   an incident.

## Data and backup posture

The Railway volume protects SQLite data from normal container replacement and
redeployment. It does not protect against accidental volume deletion,
platform-level volume loss, or operator error.

Backups stored on the same volume are not sufficient disaster recovery. Before
the pilot accumulates meaningful learner history, establish a tested,
off-platform backup export and restore procedure. Until that is complete:

- avoid deleting or replacing the volume;
- keep the service at one replica;
- verify the volume mount after infrastructure changes;
- treat the Railway project as a private pilot, not a general public service.

## Cost and access review

The deployment was created on Railway's trial plan with a single service and a
500 MB volume. Review Railway usage and billing before the trial ends. Keep AI
usage bounded with `AI_CALLS_PER_USER_PER_DAY=10`, and review the parent AI
usage display periodically.

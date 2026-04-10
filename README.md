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

Login: `user` / `password`

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

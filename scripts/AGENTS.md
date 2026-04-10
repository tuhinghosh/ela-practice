This folder contains start and stop scripts for local Docker usage on macOS, Linux, and Windows.

Container conventions used by the scripts:

- Image name: `ela-mvp`
- Container name: `ela-mvp`
- Published port: `8000:8000`
- Mounted data directory: `backend/data` -> `/app/backend/data` (SQLite persistence across restarts)

Scripts should remain minimal and deterministic for parent-friendly local use.
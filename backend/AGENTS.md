# Backend implementation guide

This backend is a FastAPI service that:

- Exposes JSON APIs under `/api/*`
- Serves the static-exported NextJS frontend assets at `/`
- Uses SQLite for persistent local data

## Current backend surface

- `app/main.py`: FastAPI entry point and API routes for auth, dashboard, activities, submission, session results, parent progress, and rewards
- `app/content_schema.py`: seeded content schema models and seed loading validation
- `app/db.py`: SQLite schema creation, core seed records, submission persistence, reward snapshots, and query projections
- `app/scoring.py`: deterministic objective + short-writing rubric scoring
- `app/ai_client.py`: OpenRouter connectivity client with safe error mapping
- `app/ai_coach.py`: constrained post-submission coaching prompt + structured-output validation and fallback
- `requirements.txt`: backend runtime dependencies

## Runtime expectations

- The backend runs in Docker
- FastAPI serves the built frontend static assets copied into `backend/static`
- Health endpoint for local checks: `GET /api/health`

## Upcoming phases

- Expand AI-specific APIs and safety contracts
- Add richer scoring/progress analytics beyond MVP baseline
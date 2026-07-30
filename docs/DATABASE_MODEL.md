# MVP database model (Part 6)

This document locks the SQLite persistence approach for MVP before deeper backend API implementation.

## Scope boundary

- SQLite stores user/app state and progress data.
- Seeded activity content stays file-based in `frontend/src/content/` during MVP.
- Database is created automatically on first backend startup.

## Relational vs JSON storage decisions

Relational columns are used for:

- Identity/ownership keys (`user_id`, `child_profile_id`, `session_id`)
- Core filtering fields (`activity_id`, `status`, timestamps)
- Numeric progress metrics (`score_percent`, `completion_count`, `stars`, `streak_days`)

JSON text columns are used for:

- Flexible metadata payloads (`metadata_json`, `evidence_json`)
- Deterministic rubric detail payloads (`rubric_json`)
- Question-evidence-based skill detail maps (`skill_breakdown_json`); untagged
  legacy questions are grouped under `overall-reading`
- Strength/growth lists (`strengths_json`, `growth_areas_json`)
- Badge arrays (`badges_json`)

`responses.evidence_json` stores the question's primary `skill_tag` and its
deterministic `score_percent`. Adaptive recommendations aggregate these
question-level observations. Legacy sessions without response evidence fall
back to their session-level `skill_breakdown_json` so existing history remains
usable.

This keeps query-critical data normalized while allowing MVP iteration without repeated migrations.

## Table set (MVP)

- `users`: login identity records (currently includes hardcoded `user`)
- `child_profiles`: one child profile per user for MVP
- `activity_sessions`: activity attempt lifecycle and timing
- `responses`: selected answers and short-written responses
- `scores`: deterministic scoring summary and rubric details per session
- `progress_snapshots`: rollup snapshots for dashboard and parent progress views
- `reward_state`: stars/streaks/badges state
- `chat_messages`: AI coach history tied to user/child/session context

Activity sessions also store an optional constrained post-completion reaction
(`fun`, `okay`, or `confusing`) and its timestamp. See
`ENGAGEMENT_EVENTS.md` for lifecycle, API, privacy, and aggregation rules.

## Example query projections implemented

- Dashboard projection:
  - username
  - reward state (stars/streak)
  - latest completion/average score summary
- Parent progress projection:
  - child display basics
  - completed session count
  - average score and last submission timestamp

## Deterministic writing rubric persistence

Rubric data is persisted inside `scores.rubric_json` with fields aligned to MVP requirements:

- `completion`
- `relevance`
- `sentence_completeness`
- `skill_specific_checks`

## Auto-creation behavior

- `backend/app/db.py` exposes `ensure_database()`.
- Backend startup calls `ensure_database()` so schema and core seed records exist automatically.

## Notes for Part 7+

- Keep content source-of-truth file-based until scope explicitly changes.
- APIs should read activity definitions from file content and write attempts/progress to SQLite.
- If/when multi-user auth expands, current foreign-key model already supports more than one user.

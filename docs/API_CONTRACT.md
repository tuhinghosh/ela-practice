# MVP API contract summary

This document captures the stable backend JSON surfaces used by the frontend in MVP.

## Auth and session

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`

## Learning flow

- `GET /api/dashboard`
- `GET /api/activities` (returns editorially reviewed activities only; supports optional `theme` and `difficulty` query filters)
- `GET /api/activities/{activity_id}`
- `POST /api/activities/{activity_id}/submit`
- `GET /api/sessions/{session_id}`

## Progress and rewards

- `GET /api/progress/parent`
- `GET /api/rewards`

## AI services

- `POST /api/ai/connectivity-check`
- `POST /api/ai/coach` (post-submission only, requires `session_id`)

## Contract notes

- Seeded activity content remains file-based in MVP.
- Activity entries include `theme` and `difficulty` fields, and `/api/activities` returns available `themes` and `difficulties` values for the reviewed child-facing library.
- The dashboard recommendation is optional. Any three distinct reviewed completions satisfy the starter phase; the original three-part path is guidance rather than a gate.
- `GET /api/dashboard` includes durable `completed_activity_ids`; starter progress and alternate selection do not depend on the three-item recent-session preview.
- Progress, reward, and chat/session history persist in SQLite.
- Validation failures return safe 4xx responses.
- Provider failures in AI routes return safe 5xx responses with bounded error messages.

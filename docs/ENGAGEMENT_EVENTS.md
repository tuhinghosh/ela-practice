# Learner engagement event contract

## Purpose and privacy boundary

The private pilot records only first-party learning-loop events needed to
understand whether activities are engaging and usable. It does not use a
third-party analytics SDK, fingerprinting, free-form child feedback, or
background behavior tracking.

## Durable session fields

`activity_sessions` remains the lifecycle source of truth:

- `status`: `started` or `submitted`;
- `started_at`: first durable activity start;
- `submitted_at`: successful submission;
- `reaction`: optional `fun`, `okay`, or `confusing`;
- `reaction_at`: time the reaction was last recorded.

Elapsed time is computed from `started_at` to `submitted_at`. A started session
that has not been submitted is an open attempt; parent summaries classify it
as abandoned only after 30 minutes. This is an analytical label, not a new
mutable status.

## API contract

### `POST /api/activities/{activity_id}/start`

Creates a started session for the authenticated active child. If that child
already has an open session for the same activity, the endpoint returns it
instead, making page refresh and resume idempotent.

Response:

```json
{
  "session_id": "uuid",
  "activity_id": "activity-id",
  "started_at": "2026-07-30 12:00:00",
  "resumed": false
}
```

### `POST /api/activities/{activity_id}/submit`

The updated frontend sends a required `session_id`. The backend verifies that
the session belongs to the authenticated user and active child, matches the
activity, and is still open. It then stores responses and scoring and marks the
session submitted atomically. Re-submission returns `409`. During the rollout,
the backend also accepts an omitted session ID for compatibility with an older
cached frontend; those legacy submissions remain valid but are excluded from
timing aggregates because they have no genuinely observed start.

### `POST /api/sessions/{session_id}/reaction`

Accepts exactly one reaction:

```json
{"reaction": "fun"}
```

Allowed values are `fun`, `okay`, and `confusing`. The session must be a
submitted session owned by the active child. Repeating the request updates the
reaction, so a mistaken tap is recoverable.

## Parent aggregation

`GET /api/progress/parent` adds:

```json
{
  "engagement": {
    "completed_with_timing": 12,
    "median_elapsed_seconds": 421,
    "open_attempts": 1,
    "abandoned_attempts": 0,
    "reactions": {"fun": 7, "okay": 3, "confusing": 2},
    "confusing_activity_ids": ["example-id"]
  }
}
```

Only aggregate engagement data appears in the parent response. Raw event rows
are not exposed to the child UI.

## Success criteria

- start is durable and idempotent across refresh;
- submission reuses and closes the owned session;
- reactions are constrained and updateable;
- median duration excludes open and legacy sessions without a real start;
- abandonment uses a documented 30-minute threshold;
- existing legacy submissions remain readable;
- backend, frontend, browser, migration, and Docker persistence tests pass.

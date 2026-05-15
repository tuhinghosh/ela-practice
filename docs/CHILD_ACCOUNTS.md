# Design: per-user child-account login

> Status: **iter N + N+1 backend complete** (commits: 71e126e memo,
> baff86a backend foundation, this commit iter 21 gates + resolver).
> Frontend child management (originally Iter N+2) is the next slice.
> Polish (parent-initiated child password reset, soft-delete UX,
> active-child banner) follows.

## Why

Today the seeded parent user owns exactly one `child_profiles` row. The
`users.role` column exists (`'parent' | 'child'`) but no child has
ever logged in: every authenticated session is the parent acting on
behalf of the single linked child. That works for the single-family,
single-child MVP, but it locks out two real product use cases:

1. **Multiple children per family.** A parent with two kids cannot give
   each their own dashboard, streak, or progress view.
2. **Direct child usage.** A child who wants to log in themselves
   (instead of the parent typing the password) has no path.

This memo plans the migration to per-user child accounts without
breaking the existing single-parent-single-child install.

## Goals

- A parent can create N child accounts. Each child gets their own
  `users` row (role `'child'`) and own login.
- A child can log in directly and see their own dashboard, submit
  activities, and receive AI coaching that's recorded against them.
- A parent can see progress for any of their children, switch between
  active children, and create new ones from the UI.
- The existing seeded parent + child profile keep working through the
  migration — no manual intervention required on existing installs.
- Tenant isolation: a child cannot read another child's session; a
  parent cannot read another family's data.

## Non-goals

- Multi-parent families (divorced/separated households, multiple
  account owners). One parent owns each child for now.
- Child-initiated password recovery. Parent retains control via the
  existing in-app rotation or DB access; a child who forgets their
  password gets a parent-initiated reset (next-iteration scope, not
  this design pass).
- Parent impersonating child (submitting activities as them). The
  parent role is read-only over child data; only the child role can
  submit. Keeps progress data honest.
- Cross-family sharing, classroom mode, anything multi-tenant beyond
  one parent per child.

## Current model recap

```
users
 ├─ id PK
 ├─ username UNIQUE
 ├─ password_hash
 ├─ role ('parent' | 'child')   -- column exists; no child rows today
 └─ created_at

child_profiles
 ├─ id PK
 ├─ user_id FK users.id  UNIQUE  -- one child per parent today
 ├─ display_name
 ├─ grade_level
 └─ created_at

activity_sessions
 ├─ user_id FK users.id          -- today: always the parent's id
 ├─ child_profile_id FK child_profiles.id
 └─ ...

reward_state
 ├─ user_id FK users.id UNIQUE   -- today: parent's id, represents the child
 └─ ...
```

Routes use `_require_authenticated_username` and look up the
`child_profiles` row via `get_child_profile_for_user(user_id)`.
Submission, AI coach, and progress all assume the user is the parent
acting for the linked child.

## Schema migration #3

The smallest set of changes that supports the goals:

1. **Drop `child_profiles.user_id UNIQUE`** so a parent can own
   multiple children. SQLite can't `ALTER TABLE DROP CONSTRAINT`; this
   requires a table recreation inside a transaction.
2. **Add `child_profiles.login_user_id INTEGER NULL`** with a unique
   *partial* index (`WHERE login_user_id IS NOT NULL`) and an FK to
   `users.id ON DELETE SET NULL` so deleting the child user keeps the
   profile rows intact for parent-side records.
3. **Add `child_profiles.is_active INTEGER NOT NULL DEFAULT 1`** so a
   parent can soft-delete a child without losing history. (Optional;
   could be deferred to a follow-up.)

Migration template (id=3, `add_child_profile_login_user_id`):

```sql
PRAGMA foreign_keys = OFF;
BEGIN;

CREATE TABLE child_profiles__new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  login_user_id INTEGER,
  display_name TEXT NOT NULL,
  grade_level INTEGER NOT NULL DEFAULT 3,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY(login_user_id) REFERENCES users(id) ON DELETE SET NULL
);

INSERT INTO child_profiles__new
  (id, user_id, display_name, grade_level, created_at)
SELECT id, user_id, display_name, grade_level, created_at
FROM child_profiles;

DROP TABLE child_profiles;
ALTER TABLE child_profiles__new RENAME TO child_profiles;

CREATE INDEX idx_child_profiles_owner ON child_profiles(user_id);
CREATE UNIQUE INDEX idx_child_profiles_login_user_id
  ON child_profiles(login_user_id)
  WHERE login_user_id IS NOT NULL;

COMMIT;
PRAGMA foreign_keys = ON;
```

Migration runner already wraps the call in a transaction-friendly
connection; the explicit `BEGIN` / `COMMIT` above is just to keep the
recreation atomic at the SQL level.

### `create_schema` parity

`db.py:create_schema` also needs the new shape so fresh installs skip
the migration step entirely. New columns: `login_user_id INTEGER` (nullable,
FK as above) and `is_active INTEGER NOT NULL DEFAULT 1`. Drop the
`UNIQUE` on `user_id` (the new index covers `login_user_id` uniqueness).

## `activity_sessions.user_id` semantics

The hard call. Today this column is the parent's user id. After the
migration, two reasonable readings exist:

**A. `user_id` = the *acting* user.** New child-submitted sessions
store the child's user id. Tenant isolation becomes:
- *Child:* `WHERE activity_sessions.user_id = my_user_id`
- *Parent:* `WHERE child_profile_id IN (SELECT id FROM child_profiles WHERE user_id = my_user_id)`

**B. `user_id` = the *owner* user (always the parent).** New child
sessions still store the parent's user id; the child is implicit via
`child_profile_id`. Tenant isolation:
- *Child:* `WHERE child_profile_id = (SELECT id FROM child_profiles WHERE login_user_id = my_user_id)`
- *Parent:* `WHERE user_id = my_user_id`

**Decision: A.** It matches the natural reading of "user_id is who did
this", makes the child's tenant-isolation query a single equality (the
hottest query on this column), and keeps the parent's "see everything
I own" query explicit and reviewable. The downside — old rows have a
parent id where the new model would have a child id — is harmless
because (a) those rows pre-date any child user, and (b) the parent's
"all my children" query covers them through the `child_profiles` join.

This decision is internal to the backend; no API contract change.

## Route role map

| Route                              | Parent | Child | Notes |
|------------------------------------|--------|-------|-------|
| `POST /api/auth/login`             | ✓     | ✓    | Both roles share the endpoint. |
| `POST /api/auth/logout`            | ✓     | ✓    | |
| `GET  /api/auth/session`           | ✓     | ✓    | Already returns `role`. |
| `POST /api/auth/password`          | ✓     | ✓    | Own password only. |
| `GET  /api/dashboard`              | ✓     | ✓    | Parent sees the active child's view; child sees their own. |
| `GET  /api/activities`             | ✓     | ✓    | Catalog is role-agnostic. |
| `GET  /api/activities/{id}`        | ✓     | ✓    | |
| `POST /api/activities/{id}/submit` | ✗     | ✓    | Parents do not submit on behalf of children — skews progress data. Returns 403 for parent role. |
| `GET  /api/sessions/{id}`          | ✓ (own children) | ✓ (own) | Tenant isolation checks change to use the resolved child_profile. |
| `GET  /api/rewards`                | ✓ (active child) | ✓ (own) | |
| `GET  /api/progress/parent`        | ✓     | ✗    | Parent-only. 403 for child. |
| `POST /api/ai/coach`               | ✗     | ✓    | Child-facing feature. 403 for parent. |
| `POST /api/ai/connectivity-check`  | ✓     | ✗    | Admin/diagnostic. 403 for child. |
| `POST /api/admin/content/reload`   | ✓     | ✗    | Already parent-gated (iter 13). |
| `POST /api/parent/child-accounts`  | ✓     | ✗    | **New.** Parent creates a child account. |
| `GET  /api/parent/child-accounts`  | ✓     | ✗    | **New.** Lists parent's owned children. |
| `POST /api/parent/active-child/{id}`| ✓    | ✗    | **New.** Sets `session["active_child_profile_id"]`. |

A new `_require_authenticated_child` dependency mirrors the existing
`_require_authenticated_parent` (iter 13). The submit / coach routes
switch to it. Parent-only routes either already use
`_require_authenticated_parent` (admin reload) or get switched to it
(parent-progress, child-account management, connectivity check).

## Active-child concept

A parent who owns N children needs to focus the dashboard on one at a
time. The session carries `active_child_profile_id`. Resolution rules:

- **Parent session, no active set:** the first child profile (by id)
  becomes active on login. If the parent owns zero children, the
  dashboard renders a friendly "Add a child" empty state instead of
  loading.
- **Parent session, active set, parent still owns that profile:** use
  it.
- **Parent session, active set but profile no longer owned (e.g.
  soft-deleted):** clear the session field and fall back to the first
  child.
- **Child session:** the active profile is unambiguously the one where
  `login_user_id = my_user_id`. The active-child setter is a no-op
  (or 403) for child sessions.

Resolution lives in a new helper, `resolve_active_child_profile(
connection, request, user)`, called by routes that need it.

## Parent UI

Minimal surface:

- **`/parent/children` page (new)** — list owned children with
  display name, grade, username, last activity. "Add a child" form
  with display_name, grade_level, username, password. Each row has a
  "Set as active" button. Optional: soft-delete via a confirmation
  modal.
- **Active child selector** — small dropdown in `AppShell` shown only
  to parents. Switches `active_child_profile_id` via
  `POST /api/parent/active-child/{id}` then triggers a router refresh.
- **`/parent/progress` updates** — title / heading reflects the
  active child's display name. The "Reward summary", per-skill,
  recent-questions, and AI-usage cards all already read from the
  resolved child profile, so the role-aware switch is centralized in
  the helper, not in every card.

## Compatibility for the seed install

1. Migration runs once at startup. The seed parent's existing child
   profile row picks up `login_user_id = NULL` (no child login yet).
2. The parent can log in unchanged. The first child profile (the
   seeded "Explorer Kid") is auto-selected as active.
3. The parent visits `/parent/children`, optionally adds a child
   login by setting a username + password on the seeded profile.
4. From then on the child can log in directly. Old activity_sessions
   keep working under the resolved "parent owns these" join.

No data loss, no env-var changes, no operator action required.

## Tests we'll need

Listed here so the implementation slices have a target.

- Migration: legacy DB pre-iter-3 shape converts cleanly; the
  partial unique index actually rejects duplicate `login_user_id`
  while accepting multiple NULLs.
- `POST /api/parent/child-accounts`: parent-only (403 for child),
  validates display_name + password length, creates both rows in
  one transaction, returns the new child profile + login info.
- `GET /api/parent/child-accounts`: lists only the calling parent's
  children, never another family's.
- `POST /api/parent/active-child/{id}`: parent can switch among owned
  children; 404 for unowned profile; 403 for child role.
- Child login: a freshly-created child can log in via the existing
  `/api/auth/login`, session has `role='child'` and the active
  profile resolves to their linked row.
- Dashboard role-switching: parent + child see the same numbers for
  the same child profile.
- Submit gating: child can submit, parent gets 403. Reward + streak
  counters increment for the right user.
- Coach gating: child can request coaching, parent gets 403. AI quota
  charges the *child's* user_id, not the parent's.
- Parent-progress gating: parent sees data, child gets 403.
- Tenant isolation: family A parent cannot read family B child's
  session id; child A cannot read child B's sessions even within the
  same family.

## Implementation slice plan

Three iterations after this memo:

**Iter N: Migration + backend role surface.**
- Migration #3 with `create_schema` parity.
- `_require_authenticated_child` dependency.
- `resolve_active_child_profile` helper.
- `POST /api/parent/child-accounts`, `GET /api/parent/child-accounts`,
  `POST /api/parent/active-child/{id}`.
- Role-gating updates on existing routes (submit, coach, parent
  progress, connectivity check).
- Tests covering everything in the test list above that's backend-
  only.

**Iter N+1: Frontend child management.**
- `/parent/children` page with list + create form.
- Active-child selector in `AppShell`.
- API client functions for the three new endpoints.
- Vitest cases for the new page + selector.
- Backend tests are unchanged from iter N; this slice is UI-only.

**Iter N+2: Polish + child-side niceties.**
- Parent-initiated child password reset endpoint + UI.
- Soft-delete (`is_active` column) end-to-end if not done earlier.
- A "currently viewing" banner on parent views so the active child is
  unmistakable.
- Tighten any tests that revealed sharp edges during iter N–N+1.

If iter N proves the design is sound, iter N+1 and N+2 can run in
either order; the iter N tests provide enough surface area for the
frontend work to consume.

## Open questions

- **Username constraints.** Children may want short / kid-friendly
  usernames. Today `users.username` is `TEXT NOT NULL UNIQUE` with
  no validator. We should probably enforce a min length (3) and
  forbid leading/trailing whitespace at the endpoint level. Decide
  during iter N implementation.
- **Multiple parents sharing custody.** Not in scope, but worth a
  five-line "we considered this and chose not to" note in the
  README's security posture section.
- **AI quota per child vs per family.** Today the quota is per
  `users.id`. After child accounts, each child user has their own
  `ai_call_log` rows. The parent gets a smaller usage column because
  they call `/api/ai/connectivity-check` only. We may want to surface
  "family total" usage on the parent view by summing across the
  parent's children — a tiny aggregation, but worth noting now so
  we don't ship a misleading "AI usage today" card.

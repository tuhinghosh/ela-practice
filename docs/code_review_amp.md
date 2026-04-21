# Code Review — ELA Reading and Writing Adventure MVP

**Reviewed:** All source code across backend, frontend, content, tests, Dockerfile, and scripts  
**Date:** 2026-04-20  
**Reviewer:** Amp (automated deep review)

---

## Summary

The project is a well-structured MVP with clear separation between a Python FastAPI backend and a NextJS static-export frontend, packaged in Docker. The learning loop (login → read passage → answer questions → get feedback → view progress) works end-to-end with real persistence. AI coaching is properly constrained with structured outputs and a deterministic fallback. Test coverage is solid across unit, integration, and E2E layers.

The review found **4 critical/high issues**, **8 medium issues**, and **5 low/informational suggestions**.

---

## Issues

### Critical / High Severity

#### 1. Path traversal in static file serving — `backend/app/main.py:561-578` (critical)

`_resolve_static_file` builds a filesystem path from the raw URL path with only `strip("/")`. Segments like `../` are not sanitized, so a request to `GET /../../etc/passwd` could serve arbitrary files outside `STATIC_DIR`.

**Impact:** An attacker can read any file readable by the container process.

**Fix:** Resolve the final path and verify it is inside `STATIC_DIR`:
```python
def _resolve_static_file(request_path: str) -> Path:
    clean_path = request_path.strip("/")
    if not clean_path:
        return STATIC_DIR / "index.html"
    target = (STATIC_DIR / clean_path).resolve()
    if not str(target).startswith(str(STATIC_DIR.resolve())):
        return STATIC_DIR / "index.html"
    # ... rest of existing logic using target
```

#### 2. Placeholder/filler text leaked into 26 reading passages — `frontend/src/content/activities.json` (high)

Two generic sentences appear across 26 activities:
- `"Scientists noticed that this subject needed more study."` — 19 occurrences
- `"These findings improved how people understood the subject."` — 7 occurrences

These sentences are out-of-context boilerplate that were inserted to satisfy the `MIN_PASSAGE_SENTENCES` and `OUTCOME_CUES` validation requirements. They break immersion for the child reader and degrade content quality.

**Example:** In `community-01` ("The Sidewalk Library"), a literary story about a girl building a free library, the passage includes *"These findings improved how people understood the subject."* mid-dialogue — completely out of place.

**Fix:** Remove the generic placeholder sentences and rewrite affected passages with natural, on-topic content that still meets the validation rules.

#### 3. Seed content re-parsed from disk on every API request — `backend/app/content_schema.py:207-208`, `main.py:137,189` (high)

`list_seed_activities()` calls `load_seed_activities()` which reads and parses `activities.json` from disk, validates all 79 activities with regex, and rebuilds Pydantic models — on every single request to `/api/dashboard`, `/api/activities`, `/api/activities/{id}`, and `/api/activities/{id}/submit`.

**Impact:** Unnecessary I/O and CPU on every request. With 79 activities and multi-paragraph validation, this measurably slows the server.

**Fix:** Cache the result at module level or use `functools.lru_cache`:
```python
@functools.lru_cache(maxsize=1)
def list_seed_activities() -> tuple[ActivityModel, ...]:
    return tuple(load_seed_activities())
```

#### 4. Activity fallback creates broken submit state — `frontend/src/app/activity/[activityId]/activity-client.tsx:43-53` (high)

When the backend fetch fails, the component falls back to local mock data and renders those questions. However, when the child clicks "Submit answers", the submission still goes to the live backend API — which will reject the request because the mock question IDs may not match the live activity.

**Fix:** When the API fetch fails, disable the submit button or show a blocking error instead of rendering the mock fallback as if it's a real activity.

---

### Medium Severity

#### 5. Weak default session secret — `backend/app/main.py:45` (medium)

`SESSION_SECRET` defaults to `"ela-dev-session-secret"` if the environment variable is not set. While acceptable for local MVP use, this allows session cookie forgery if the app is ever exposed beyond localhost.

**Fix:** Log a warning on startup if using the default, or generate a random secret when `SESSION_SECRET` is missing.

#### 6. No client-side form validation before submission — `activity-client.tsx:60-86` (medium)

The child can click "Submit answers" without answering any questions. This sends empty/undefined answers to the backend, resulting in a 422 error (for multiple-choice) or a 0% score with no useful feedback (for short-response).

**Fix:** Validate that all questions have answers before calling `submitActivity`. Show a friendly message like "Please answer all questions before submitting."

#### 7. 422 error messages display as `[object Object]` — `frontend/src/lib/api.ts:23-24` (medium)

FastAPI returns 422 validation errors as `{ detail: [{ msg: "...", loc: [...] }] }`. The frontend `request()` function tries `payload.detail`, but since `detail` is an array, it renders as `[object Object]`.

**Fix:** Check if `payload.detail` is an array and extract readable messages:
```typescript
if (Array.isArray(payload.detail)) {
  message = payload.detail.map((d: any) => d.msg).join("; ");
}
```

#### 8. Streak counter increments on every submission, not per calendar day — `backend/app/db.py:532` (medium)

`streak_days = previous_streak + 1` runs on every submission, so submitting three activities in one day gives a 3-day streak. This misrepresents the motivational metric.

**Fix:** Compare the current date against `updated_at` in `reward_state` and only increment if the last submission was on a different calendar day.

#### 9. `get_session_result` does not verify session ownership — `backend/app/main.py:401-424` (medium)

Any authenticated user can view any session by guessing/enumerating UUIDs. The `/api/ai/coach` endpoint correctly checks `session["user_id"] != user["id"]`, but `/api/sessions/{session_id}` does not.

**Fix:** Add the same ownership check used in the coach endpoint.

#### 10. Content validation logic duplicated across Python and TypeScript — `backend/app/content_schema.py` and `frontend/src/lib/content-schema.ts` (medium)

The sentence counting, paragraph splitting, cue detection, difficulty assignment, and validation rules are fully duplicated in both languages (~250 lines each). Any rule change requires updating both files in lockstep.

**Fix:** Designate the backend as the single source of truth for validation. Reduce the frontend `content-schema.ts` to type definitions and minimal parsing only (for static build and fallback display).

#### 11. Scoring heuristics are easily bypassed — `backend/app/scoring.py:26-31` (medium)

The `relevance` check passes if *any* 3+ character word overlaps with the passage text (e.g., "the", "was"). The `sentence_completeness` check passes if the text has 5 words and any `.`, `!`, or `?` character. A child could type "apple banana orange grape pear." and get full points.

**Fix:** Require a minimum number of matching non-stopword tokens (e.g., 3+) for relevance. This is a known MVP trade-off, but the current threshold is too low to provide meaningful learning signal.

#### 12. Docker container runs as root — `Dockerfile:12-30` (medium)

The runtime stage has no `USER` directive, so uvicorn runs as root inside the container.

**Fix:** Add a non-root user:
```dockerfile
RUN useradd -m appuser
USER appuser
```

---

### Low / Informational

#### 13. Hardcoded nav links to specific mock activity/session IDs — `frontend/src/components/app-shell.tsx:16-19`

The navigation bar includes `{ href: "/activity/nature-01" }` and `{ href: "/results/session-001" }`. These only work if that exact activity/session exists. After the child completes real sessions, the "Results" link still points to a mock session.

**Suggestion:** Either remove these hardcoded links or make them dynamic based on the user's most recent session.

#### 14. `frontend/out/` (build output) is committed to git — `.gitignore`

The `frontend/out/` directory contains the static export build artifacts. These should typically be in `.gitignore` since the Dockerfile rebuilds them.

#### 15. `DeterministicWritingRubricModel` is defined but never used — `backend/app/content_schema.py:97-101`

This Pydantic model is declared but never referenced anywhere in the codebase.

#### 16. Multiple `import re` / `import json` inside functions — `backend/app/content_schema.py:105,111,117,140`

Several utility functions in `content_schema.py` import `re` and `json` inside the function body rather than at the top of the module. This is a minor style inconsistency.

#### 17. `question_feedback` field in submit response is undocumented in the frontend API types — `frontend/src/lib/api.ts:85-110`

The backend submission response includes a `question_feedback` key with per-question scoring details, but the `SubmitResponse` type in the frontend API client omits it. This data could be useful for showing the child which specific questions were correct.

---

## Architecture Observations

### What works well

- **Clean API contract**: The typed API client (`frontend/src/lib/api.ts`) and the FastAPI routes share a consistent, well-documented shape. The `docs/API_CONTRACT.md` stays accurate.
- **AI safety guardrails**: The coach system prompt is constrained, structured outputs are validated with Pydantic, and a deterministic fallback exists for invalid AI responses. The child question input is length-limited (220 chars).
- **Test coverage**: 7 backend test files cover auth, scoring, DB modeling, API routes, AI connectivity, AI coach, and content schema. 4 frontend unit test files and 5 E2E specs cover navigation, rewards, AI coach, parent progress, and seeded content rendering.
- **Reward system**: Stars, streaks, badges, and points are computed server-side and persisted, with a snapshot attached to each session for post-activity celebration.
- **Schema and content validation**: Passages are validated for minimum sentence counts, paragraph structure, narrative arc cues, and question consistency — both in the backend schema and in tests.

### Areas for improvement

- **Database connection management**: `get_connection()` returns a raw `sqlite3.Connection` used as a context manager. The `with` statement calls `connection.close()`, but `insert_chat_message` calls `connection.commit()` inside the `with` block in `main.py` after the connection from the first `with` block has already been closed and a new one opened. This works but is fragile.
- **No loading/skeleton states**: Frontend screens show either live data or mock fallback data. There's no loading spinner or skeleton state while API calls are in flight, which can cause a flash of mock content before real data loads.
- **No React error boundary**: If a runtime error occurs in any component, the entire app crashes with a white screen. A top-level error boundary would improve resilience.
- **Progress snapshots grow unboundedly**: Every submission inserts a new `progress_snapshots` row. Over time this table will grow without pruning, though this is fine for MVP scale.

---

## Test Coverage Assessment

| Area | Coverage | Notes |
|------|----------|-------|
| Auth flow | ✅ Good | Login, logout, session check, invalid cookies, protected routes |
| Activity submission | ✅ Good | Full flow, repeat submissions, reward accumulation |
| Scoring | ✅ Good | Shape validation, determinism |
| AI coach | ✅ Good | Success, fallback on invalid JSON, provider/key errors |
| Content schema | ✅ Good | All 79 activities validated, passage length, difficulty distribution |
| Parent progress | ✅ Good | Empty state, populated state, trend/skill summary |
| Frontend components | ⚠️ Basic | Only AppShell and AICoachPanel have unit tests |
| E2E | ✅ Good | Navigation, reward UI, AI coach, parent progress, seeded content |

### Missing test coverage

- No test for path traversal in `_resolve_static_file`
- No test for session ownership enforcement on `/api/sessions/{session_id}`
- No test for submitting without answering all questions (client-side validation)
- No unit tests for `Button`, `Card`, `Tag`, `Layout` components
- No test for the home page (`page.tsx`) filtering/mission selection logic

---

## Recommended Priority Order

1. **Fix path traversal** (critical security — issue #1)
2. **Remove placeholder text from passages** (high content quality — issue #2)
3. **Cache seed activities** (high performance — issue #3)
4. **Block submission on fallback data** (high correctness — issue #4)
5. **Add session ownership check** (medium security — issue #9)
6. **Fix streak logic** (medium correctness — issue #8)
7. **Add client-side form validation** (medium UX — issue #6)
8. **Fix 422 error display** (medium UX — issue #7)
9. **Add non-root Docker user** (medium security — issue #12)
10. Everything else

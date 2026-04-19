# Code review

Date: 2026-04-16
Scope: full repository (backend FastAPI, NextJS frontend, seeded content, Docker, scripts, docs, tests)
Reviewer perspective: pre-Phase-13 hardening pass against MVP scope locked in `docs/PLAN.md` and `AGENTS.md`.

This review is structured as: (1) overall summary, (2) what's working well, (3) issues grouped by severity, (4) per-area notes, (5) prioritized recommendations. Severity reflects MVP context (local Docker, single hardcoded user, child practice app), not a production SaaS bar.

---

## 1. Summary

The codebase is in a good state for the locked MVP. Architecture matches the plan: FastAPI serves a NextJS static export at `/`, JSON API under `/api/*`, SQLite for state, OpenRouter for AI coaching with structured-output validation and a deterministic fallback. Tests exist at backend (pytest), frontend unit (Vitest), and end-to-end (Playwright) layers. Schemas are validated twice (Pydantic in Python, hand-rolled validators in TS) which catches malformed seeded content early.

The most material issues are **content quality** (templated boilerplate text padding the seeded passages, which leaks into scoring), a few **scoring/reward semantics** that don't match their names (skill breakdown, streak counting, "strengths"), and a handful of **state-management quirks in the frontend** introduced by static-export constraints. None block the MVP, but several should be cleaned up before expanding scope.

---

## 2. What's working well

- **Clean module boundaries.** `main.py` (routes), `db.py` (SQL + projections), `scoring.py` (deterministic), `ai_coach.py` (LLM contract + fallback), `ai_client.py` (HTTP) keep concerns well separated. Each is small and readable.
- **AI safety posture.** `ai_coach.py:21-29` defines a tight system prompt; structured output is validated through `CoachOutputModel` (`ai_coach.py:9-18`); `_extract_json_object` is forgiving but bounded; fallback path always returns a safe payload (`ai_coach.py:61-97`); failure modes in `main.py:498-511` map cleanly to 502/503 with bounded user-facing detail. This matches the locked AI contract well.
- **Seeded content is gated by real validators.** `backend/app/content_schema.py:126-183` enforces theme membership, paragraph counts, sentence counts, narrative-cue presence, MC choice integrity, and absence of `correctChoice` on short-response items. Mirrored in `frontend/src/lib/content-schema.ts`. Failures fail loudly at startup / module load, which is correct.
- **Tests cover the critical paths.** `test_api_routes.py` exercises login → list → detail → submit → session → progress with persistence assertions. `test_ai_coach.py` covers schema-success, schema-failure→fallback, and route-level 200/502/503. `test_db_modeling.py` confirms idempotent `ensure_database()`. `test_seed_content_schema.py` checks structural invariants of the content library. Frontend Playwright suites mock backend responses and exercise the AI-coach failure path.
- **Auth is appropriately minimal.** Signed cookie session via `SessionMiddleware` (`main.py:55-61`); `_require_authenticated_username` dependency centralizes the check; static-route protection logic in `main.py:541-590` is small and readable.
- **Reward snapshot persists with the session.** Storing the snapshot in `activity_sessions.metadata_json` lets the results screen replay celebration state without re-deriving from history (`db.py:526-529`, `main.py:408-423`). Good MVP choice.
- **Idempotent DB lifecycle.** `ensure_database()` / `INSERT OR IGNORE` / `CREATE TABLE IF NOT EXISTS` mean a fresh container and a re-started container behave the same. Verified by `test_existing_database_reuse_path_keeps_data`.
- **Docker build is small and ordered.** Multi-stage build, `npm ci`, copies `requirements.txt` before backend source so layer caching works. `python:3.12-slim` and `node:22-alpine` are current.

---

## 3. Issues by severity

### High — content quality (affects scoring + child experience)

**Templated boilerplate padding in passages.** `frontend/src/content/activities.json` has 79 activities, but the same generic sentences are reused across many of them:

- `"By the end, they understood ..."` appears in 58 of 79 passages.
- `"A field note about habitat conditions explained why the change occurred."` appears 7 times.
- `"They traced patterns in plants, soil, and weather to support their claim."` appears 7 times.

Concrete example: `forest-friends` is a literary story about a child watching birds build a nest, but the second paragraph contains "A field note about habitat conditions explained why the change occurred. They compared two observations from different spots along the trail." (`activities.json:9`). The text is off-topic and reads like filler added to satisfy the `MIN_PARAGRAPH_SENTENCES = 7` and `OUTCOME_CUES` requirements in `content_schema.py:34-60`.

Why this matters beyond aesthetics:
1. Children read off-topic, jarring filler.
2. Scoring uses passage tokens for "relevance" (`scoring.py:25-26`). When passages contain generic words like "evidence", "observed", "pattern", almost any short response will pass the relevance check by token overlap. This silently inflates scores.
3. The narrative-arc validator is doing its job structurally but is being satisfied by padding rather than authored content — a false sense of curation.

**Recommendation:** treat the structural validators as authoring guides for new content, but rewrite the existing passages so the second paragraph is genuinely on-topic. Consider lowering `MIN_PASSAGE_SENTENCES`/`MIN_PARAGRAPH_SENTENCES` if they're forcing padding. Alternatively, add a validator that fails when the same sentence appears in more than ~3 activities.

### High — `skill_breakdown` and "strengths/growth" are misleading

`scoring.py:103` returns `{tag: round(score_percent, 2) for tag in activity.skillTags}` — every skill in an activity gets the *same* number, the activity's overall percent. So "skill breakdown" is not a per-skill measurement at all. Then `db.py:474-475` computes:

```python
strengths = [tag for tag, value in scoring_payload["skill_breakdown"].items() if value >= 75]
growth_areas = [tag for tag, value in scoring_payload["skill_breakdown"].items() if value < 75]
```

Consequences:
- For any single activity, *all* its skill tags are simultaneously strengths or simultaneously growth areas — never split.
- Each new submission overwrites strengths/growth with only the tags from that one activity (no aggregation across history).
- The dashboard "Strongest area" and "Growth area" surfaced in `main.py:366-369` and `frontend/src/app/parent/progress/page.tsx:34-35` therefore reflect the *most recent* activity, not a learner profile.

**Recommendation:** either (a) drop the per-skill claim entirely and only show overall scores in MVP, or (b) compute strengths/growth as rolling averages per skill across `scores` history, using `JOIN`s in a single query over `activity_sessions ⋈ scores`. Option (a) is the smallest honest change.

### Medium — "streak" increments per submission, not per day

`db.py:498-499`: `streak_days = previous_streak + 1` runs on every submission. Two submissions in one day add two days to the streak; a day with zero submissions does not break it. This contradicts the natural meaning of "streak" displayed in the dashboard and parent view, and makes the badge-unlock heuristic loose.

**Recommendation:** compute streak from `submitted_at` dates: increment if the latest submission's date is exactly one day after the prior streak's last day, keep if same day, reset to 1 otherwise. Persist `last_streak_date` on `reward_state` to avoid recomputing from history.

### Medium — synchronous OpenRouter call inside async FastAPI app

`ai_client.py:74-80` uses `httpx.post(...)` (synchronous) with a 20s timeout. The route handlers in `main.py` are declared `def` (not `async def`), so FastAPI runs them on the threadpool — meaning a slow OpenRouter call ties up a worker thread but doesn't block the event loop. This is acceptable for a single-user MVP, but the mismatch is easy to break later by switching a route to `async def`. Either:

- Keep handlers sync intentionally (document it), or
- Switch to `httpx.AsyncClient` and make the AI routes `async def`.

A minor related point: `ai_client.py:96-98` has inconsistent indentation in the `messages` list literal (extra leading spaces). Cosmetic only.

### Medium — missing pinning and missing `pydantic` in `requirements.txt`

`backend/requirements.txt`:

```
fastapi
uvicorn[standard]
itsdangerous
httpx
```

- No version pins. Builds today and builds in three months can produce different dependency trees, especially because Pydantic v1 → v2 migrations can break `model_validate` / `Field(min_length=...)` usage in `content_schema.py` and `ai_coach.py`.
- `pydantic` is used directly (`from pydantic import BaseModel, Field, ValidationError`) but not listed — relies on it being a FastAPI transitive dep. List it explicitly.
- `httpx` is in *both* `requirements.txt` and `requirements-dev.txt`. Drop the dev copy.

**Recommendation:** add a `uv.lock` (the project already uses `uv` per `AGENTS.md`) or pin minor versions in `requirements.txt`, list `pydantic>=2,<3`, and trim `requirements-dev.txt`.

### Medium — `progress_snapshots` grows unbounded

Every submission inserts a row (`db.py:477-491`). Reads use `ORDER BY captured_at DESC LIMIT 1`. Over time, this table accumulates one row per submission forever, even though only the latest is consulted. Not urgent for a single-user local app, but easy to fix and noted in `DATABASE_MODEL.md` as an "aggregated rollup" — which the current implementation contradicts.

**Recommendation:** either `UPSERT` a single snapshot per `(user_id, child_profile_id)` or periodically prune old rows. Same `(user_id, child_profile_id)` is unique-friendly today.

### Medium — frontend hidden coupling to mock IDs in static export

`frontend/src/components/app-shell.tsx:15-20` hardcodes nav links to `/activity/forest-friends` and `/results/session-001`. `frontend/src/app/results/[sessionId]/page.tsx:6-8` uses `recentSessions` (mock data) for `generateStaticParams`. After a real submission, `frontend/src/app/activity/[activityId]/activity-client.tsx:72` navigates to `/results/session-001?session=<real-uuid>` — i.e. it *reuses* the prebuilt `session-001` route as a generic shell and passes the real session UUID via query string.

This works but is fragile and surprising:
- If `recentSessions` is renamed/cleared, the static route disappears and runtime navigation 404s.
- The "Results" nav link in `AppShell` always points to `session-001` regardless of context.
- Children/parents could refresh `/results/session-001?session=<uuid>` and get the same content; refreshing without `?session=` would show the mock fallback silently (`results-client.tsx:103-119`).

**Recommendation:** document this static-export workaround prominently (or in a code comment near `generateStaticParams`), or generate a single catchall like `/results/view?session=<uuid>` and stop pretending the URL slug is the session id. Same comment applies to the `/activity` nav link.

### Medium — `localStorage` and SSR-mismatch risk in `app/page.tsx`

`page.tsx:84` reads `localStorage.getItem("ela:suggested-activity")` directly during render with a `typeof window !== "undefined"` guard. With static export this *currently* runs only client-side (no SSR), so it works, but it means the value can change between the static HTML snapshot and the first React paint and React 19 strict mode may warn. Same code in `results-client.tsx:85` writes to `localStorage` from a `requestCoach` callback — that one is fine.

**Recommendation:** move the read into a `useEffect` that sets state, then derive `suggestedActivityId` from state. Also consider namespacing under a per-user key once multi-user lands.

### Low — catch-all static route silently 302s every unknown path

`main.py:581-593`: `serve_static` redirects any non-public, non-protected path to `/`. That's intentional for SPA-ish routing, but it also means hitting `/api/typo` returns a 302 instead of a JSON 404, which complicates client-side debugging. Plus `_resolve_static_file` falls back to `index.html` when nothing matches (`main.py:578`), which means even a `/foo/bar/baz.js` style request will load the SPA HTML instead of 404'ing — content-type confusion possible.

**Recommendation:** explicitly 404 unknown paths under `/api/`, and only fall back to `index.html` for routes that look like client-side app paths.

### Low — `DASH BOARD` mission is hardcoded to `activities[0]`

`main.py:138`: `mission = activities[0]`. Combined with `_apply_default_difficulties` sorting by `id` (`content_schema.py:120-123`), this means the first alphabetic activity is always the canonical "today's mission" surfaced by the dashboard. It's harmless because the frontend has its own selection logic that overrides this, but the contract returned by `/api/dashboard` is misleading.

**Recommendation:** either rotate by date (deterministic per day), pick something not yet attempted by `child_profile_id`, or remove the mission from the dashboard payload and let the frontend choose.

### Low — `responses.evidence_json` is dead

`db.py:64-73` defines the column and `db.py:447-451` always inserts `{}`. Either populate it (e.g., per-question rubric facets from `scoring.question_feedback`) or remove the column. Keeping unused columns invites confusion later.

### Low — missing `.env.example`

Root `.env` is gitignored but there is no `.env.example` to tell a new contributor what's needed (`OPENROUTER_API_KEY`, optionally `OPENROUTER_MODEL`, `SESSION_SECRET`, `DATABASE_PATH`). The README only mentions Docker, not env vars.

**Recommendation:** add `.env.example` with placeholders and a one-line README pointer.

### Low — `SESSION_SECRET` defaults to a literal in code

`main.py:45`: `SESSION_SECRET = os.environ.get("SESSION_SECRET", "ela-dev-session-secret")`. Fine for local MVP, but it would be very easy to ship this default to a non-local environment unnoticed. Either log a warning when the default is used, or refuse to start when running outside of `dev` without it.

### Low — no `pytest` config; reliance on naming conventions

There's no `pytest.ini` / `pyproject.toml` / `conftest.py` (top-level). `pytest-asyncio` is in dev requirements but `asyncio_mode = auto` is not configured; tests use `@pytest.mark.asyncio` explicitly, which is fine but worth noting that any new async test must remember the marker. Add a minimal `pyproject.toml` with `[tool.pytest.ini_options] asyncio_mode = "auto"` to remove the foot-gun.

### Low — Playwright suite tests against `next dev`, not the production-served bundle

`playwright.config.ts:10-15` boots `npm run dev` (NextJS dev server, port 3000). The real production flow is "static export served by FastAPI on 8000". Auth redirects in `main.py:582-590` are therefore not exercised by E2E. Consider adding one Playwright smoke that hits the Docker container on 8000 (or starts FastAPI directly with a built `frontend/out`).

### Low — small typo / formatting nits

- `main.py:277` has an extra-indented `status_code=` argument (visually misleading though syntactically fine).
- `ai_client.py:96-98` `messages` list has inconsistent leading whitespace.
- `content_schema.py` does `import re` and `import json` *inside* functions (`_count_sentences`, `load_seed_activities`, `list_seed_themes`). Move to the top of the module.
- `db.py:497`: `int(round(scoring_payload["score_percent"] / 25))` — Python's `round` is banker's rounding, so e.g. 50% → 2 stars, 50.5% → 2 stars. Probably fine, but worth being explicit if the product wants 50% → 2.

### Low — `frontend/CLAUDE.md` is just `@AGENTS.md`

Pointer-only; harmless but worth noting that any updates to AGENTS.md should remember Claude Code is reading it as the frontend project guide.

---

## 4. Per-area notes

### Backend

- `main.py` route handlers re-load seeded content on every call via `list_seed_activities()` / `get_seed_activity()` (`content_schema.py:186-212`), which re-reads + re-validates JSON. For 79 activities this is fine in dev; if the library grows, cache once at startup.
- `_require_authenticated_username` returns the username string, then nearly every handler immediately re-queries `users` to get its id (`main.py:140-144`, `261-263`, etc.). Resolving and caching the `(user_id, child_profile_id)` on the session at login would simplify handler bodies.
- `submit_activity` validates `question_type` against the user's payload (`main.py:280-309`) but does not reject answers for questions the user *omitted*. Backend silently scores omitted short-response questions as missing, which is correct, but no error is raised for partial submissions. The front-end has no client-side guard either — easy footgun for an inexperienced child.
- `db.py:171-253` `insert_demo_progress_records` is only used by tests but lives in `db.py`. Moving it to a `tests/fixtures.py` would clarify the production surface of `db.py`.
- `db.py:381-410` `get_recent_writing_feedback` rebuilds rubric summary text each call. The summary string template is inlined; if the parent view wants to render this richly later, return the structured rubric and let the frontend format it.

### Scoring

- `_score_short_response` (`scoring.py:20-58`) is reasonable for MVP. The token-overlap "relevance" check is biased toward children who copy passage words verbatim — which is the opposite of what good summarization rewards. Minor; flag for the next rubric pass.
- `_tokenize` filters tokens shorter than 3 characters (`scoring.py:8`), which throws away words like "is/it/he/she" — fine for relevance, but means a 4-word answer like "He had to" gets zero relevant tokens.
- `score_activity_submission` derives the rubric from "the first short-response question's details" (`scoring.py:80-88`). If an activity has multiple short-response questions, the second one's facets are silently ignored. Not a bug today (every seeded activity has at most one short-response Q), but document it.

### Content schema

- The two-implementation parity (Python and TS) is intentional but they will drift. Consider generating one from the other (e.g., emit JSON Schema from Pydantic, validate from TS). For MVP, the duplication is acceptable — but add a comment in both files reminding maintainers to update the other.
- `_apply_default_difficulties` round-robins by sorted ID (`content_schema.py:118-123`). It will rebalance every time a single activity is added or renamed, potentially flipping difficulty for unrelated activities. Pin difficulty in the JSON instead.

### Frontend

- `app/page.tsx:62-79` has two parallel-shape mappings (backend response → view model) and (mock fallback → view model). Extract a single `toMissionItem(...)` helper to avoid divergence.
- `activity-client.tsx:21` and `results-client.tsx:45-48` use `useMemo` over deps that include `activityId`/`initialSessionId` only — fine — but the mock-data fallback shape isn't quite the same as the real API shape (`fallback.passageType` vs `passage_type`). The component uses `resolved.passage_type` for the API shape and `passage_type: fallback.passageType` for the fallback (`activity-client.tsx:43-53`). Works, but make the fallback a real `ActivityDetailResponse` to remove the conditional shape hopping.
- `LogoutButton` (`logout-button.tsx`) doesn't await navigation — it calls `fetch(...)` then `window.location.href = "/login"` inside `finally`, which fires before the response is parsed. This is fine because `/api/auth/logout` is fire-and-forget, but a failed network call still navigates to `/login` (the user just looks logged out without actually being). Acceptable for MVP.
- Multi-question state in `activity-client.tsx:23` is keyed by `question.id` and never typed (`Record<string, string>`). Once short-response questions accept multi-line answers it's fine; if you add new question types (e.g., ordered sequence), tighten the type.

### Tests

- `test_api_routes.py:139-156` `test_repeat_submissions_are_predictable` proves the streak bug: `streak_after == previous + 1` per submission (line 152). The test currently *codifies* the misbehavior. When fixing the streak semantics, update this test.
- `test_seed_content_schema.py` is well-designed for structural invariants but does not catch the *content quality* problems noted above (boilerplate reuse). Consider adding a duplication check.
- The frontend Playwright suite mocks all `/api/*` routes — useful for UI regression but no E2E coverage of the FastAPI ↔ static-export integration. See "Playwright suite tests against `next dev`" above.

### Docker / scripts

- Scripts duplicate the same body across mac/linux/windows. Acceptable for clarity. The `ela-mvp` container name is reused — `start` stops any prior instance (`start-mac.sh:10-12`), which is correct.
- Dockerfile copies `frontend/src/content/` into `backend/content/` (`Dockerfile:26`). `content_schema.py:26-29` then *prefers* `backend/content` if present. This means the runtime image has two copies of the seed files (the Python copy and the static JS bundle). Saves a relative-path read across mounted volumes; cost is minor disk + a confusing dual-source-of-truth. Worth a one-line comment in `content_schema.py` explaining why.
- `.dockerignore` excludes `docs` (good) and `.env` (good), but not `backend/data/` — meaning local `.sqlite3` files can be baked into the image if a dev forgets to clean up. Add `backend/data/`.

### Docs

- `docs/PLAN.md`, `docs/API_CONTRACT.md`, `docs/CONTENT_MODEL.md`, `docs/DATABASE_MODEL.md`, `docs/MVP_LIMITATIONS_AND_NEXT_STEPS.md`, `AGENTS.md`, and per-folder `AGENTS.md` files agree with each other and with the implementation. Good discipline.
- `docs/DATABASE_MODEL.md` says `progress_snapshots` is for "aggregated completion and skill progress data used by dashboard and parent views" — but the current implementation appends rather than aggregates (see Medium issue above).
- `docs/CONTENT_MODEL.md` describes the deterministic enrichment-on-load behavior that no longer matches the code: the schema enforces minimum sentence counts at validation time and *refuses* short content rather than enriching it. Update the doc.
- `CLAUDE.md` (root) and `frontend/CLAUDE.md` (which simply imports `frontend/AGENTS.md`) are both consistent with the codebase as of this review.

---

## 5. Prioritized recommendations

**Before adding more features:**

1. Rewrite the second paragraph of every seeded activity to be on-topic. Add a duplication guard to `load_seed_activities`.
2. Decide what `skill_breakdown` actually means. Either drop it from the API and UI, or compute it per-skill from response-level facets.
3. Fix the streak counter to be date-based; update `test_repeat_submissions_are_predictable` accordingly.
4. Add `.env.example` and pin Python dependencies (and explicitly list `pydantic`).

**Soon after:**

5. Cache `list_seed_activities()` at process start.
6. Replace the `/results/session-001?session=<uuid>` workaround with a single static results route, e.g. `/results/view`.
7. Move `localStorage` reads in `app/page.tsx` into `useEffect`.
8. `UPSERT` `progress_snapshots` per `(user_id, child_profile_id)` instead of appending.
9. Either delete `responses.evidence_json` or populate it from `question_feedback`.
10. Add one Playwright smoke test against the production Docker bundle (port 8000) to cover the auth-redirect path the static-export server actually uses.

**Nice-to-have polish:**

11. Move `import re` / `import json` in `content_schema.py` to module top.
12. Pin difficulty in `activities.json` rather than auto-assigning at load.
13. Add a `pyproject.toml` with `asyncio_mode = "auto"` for pytest-asyncio.
14. Replace synchronous `httpx.post` with `AsyncClient` (or document why handlers stay sync).
15. Log a startup warning if `SESSION_SECRET` is the default value.

---

## Appendix — files reviewed

Backend: `backend/app/main.py`, `db.py`, `scoring.py`, `ai_coach.py`, `ai_client.py`, `content_schema.py`, `__init__.py`; `backend/tests/test_api_routes.py`, `test_scoring.py`, `test_auth.py`, `test_db_modeling.py`, `test_ai_coach.py`, `test_ai_connectivity.py`, `test_seed_content_schema.py`; `backend/requirements.txt`, `requirements-dev.txt`; `backend/AGENTS.md`.

Frontend: `frontend/src/app/{layout,page,login/page,parent/progress/page,activity/[activityId]/page,activity/[activityId]/activity-client,results/[sessionId]/page,results/[sessionId]/results-client}.tsx`; `frontend/src/components/{app-shell,ai-coach-panel,button,card,tag,layout,logout-button}.tsx`; `frontend/src/components/{ai-coach-panel,app-shell}.test.tsx`; `frontend/src/lib/{api,content-schema,mock-data}.ts` and `.test.ts`; `frontend/src/content/{activities,skill-tags,themes}.json`; `frontend/tests/e2e/*.spec.ts`; `frontend/{package.json,next.config.ts,playwright.config.ts,vitest.config.ts,vitest.setup.ts,tsconfig.json,AGENTS.md,CLAUDE.md}`.

Infra/docs: `Dockerfile`, `.dockerignore`, `.gitignore`, `scripts/{start,stop}-{mac,linux}.sh`, `scripts/start-windows.ps1`, `scripts/AGENTS.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/{PLAN,API_CONTRACT,CONTENT_MODEL,DATABASE_MODEL,MVP_LIMITATIONS_AND_NEXT_STEPS}.md`.

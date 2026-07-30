# High level steps for project

This document turns the MVP into a staged execution plan. Each part includes implementation tasks, tests, and success criteria.

Important planning notes:
- This app starts from scratch; there is no existing reading-app frontend to adapt
- The stack should match the Kanban example: NextJS frontend, FastAPI backend, SQLite, OpenRouter, Docker, and local scripts
- For MVP, NextJS should be built as a static export and served by FastAPI at `/` (no SSR routing in v1)
- The experience should feel fun and child-friendly, but the first version must still be small and practical
- The MVP should focus on a narrow set of third-grade reading and writing skills before expanding further
- Seeded reading content should live in local files first; SQLite should persist attempts, progress, rewards/streaks, and chat/session history
- The MVP test stack is fixed: backend `pytest` + `httpx`, frontend unit/component `vitest` + React Testing Library, and end-to-end/integration `playwright`

The post-MVP content quality audit and reviewed-library expansion plan is in
[`CONTENT_AUDIT_AND_EXPANSION_BLUEPRINT.md`](CONTENT_AUDIT_AND_EXPANSION_BLUEPRINT.md).
The 27-activity production specification for the reviewed-core expansion is in
[`CONTENT_PRODUCTION_MATRIX_27.md`](CONTENT_PRODUCTION_MATRIX_27.md).

## Post-MVP content expansion

### Batch 0 — Content quality guardrails

- [x] Add an explicit reviewed/draft/rewrite-required registry
- [x] Add a deterministic content-audit command
- [x] Gate reviewed difficulty, question tags, feedback, and informational sources
- [x] Check answer-position predictability and duplicate language
- [x] Keep reviewed adaptation separate from legacy/draft content
- [x] Model reading and writing evidence separately for constructed responses
- [x] Pass backend, frontend, and production Docker verification

### Reviewed-core expansion reporting

- [x] Report reviewed activity coverage by reading skill and difficulty
- [x] Show remaining gaps to the four-activities-per-cell target
- [x] Fail CI when any verified coverage cell regresses
- [x] Draft the nine-activity mixed-difficulty Release A
- [x] Review, revise, and approve Release A
- [x] Draft, sample, approve, and verify Release B
- [x] Meet the four-activities-per-cell skill-by-difficulty target
- [x] Produce Release C for portfolio variety and answer-position balance

### Learner engagement evidence

- [x] Define the private first-party lifecycle and reaction API contract
- [x] Persist idempotent activity starts and reuse them on submission
- [x] Add constrained post-activity reactions
- [x] Add parent-only duration, abandonment, and reaction aggregates
- [x] Verify migration, API, frontend, browser, and Docker persistence behavior

## Locked MVP decisions

These decisions are intentionally locked for MVP implementation unless explicitly changed later:

- Root `AGENTS.md` is the main project guide; do not create `docs/AGENTS.md` for now
- `docs/PLAN.md` remains in `docs/` as the phased execution plan
- `frontend/AGENTS.md` should be created only after the frontend scaffold exists
- NextJS runs as a static export served by FastAPI at `/`; no SSR-style Next routing in v1
- Auth is backend-issued from the start with one login endpoint, one logout endpoint, and one signed cookie-based session
- The high-level route map should be locked in `docs/` before scaffolding; only minor implementation-driven adjustments are expected in Parts 2 and 3
- Short written responses use deterministic rubric scoring in MVP (AI provides coaching/explanations but is not the primary scorer)
- The AI coach appears after answer submission only in MVP (no live hint-on-demand during answering)
- Seeded content is file-based initially; SQLite persists attempts, progress, rewards/streaks, and chat/session history
- The default test stack is fixed as listed above

---

## Part 1: Product and implementation plan

### Goals
- Convert the high-level idea into a concrete MVP scope
- Lock the learning loop, domain model, API surfaces, and phased build plan
- Ensure the plan is approved before major implementation begins

### Checklist
- [x] Confirm the target user flow from parent setup to child practice
- [x] Confirm the MVP learning loop: choose mission -> read passage -> answer questions -> get feedback -> save progress
- [x] Confirm the initial skill scope for MVP
- [x] Confirm which features are child-facing versus parent-facing
- [x] Confirm which features are deterministic in v1 and which are AI-powered
- [x] Lock the initial high-level route map for the frontend in `docs/` before scaffolding
- [x] Define the initial backend API surface
- [x] Define the initial database entities
- [x] Define the structured output contract for AI coaching
- [x] Confirm root `AGENTS.md` is the single main project guide for now (no `docs/AGENTS.md`)
- [x] Note that `frontend/AGENTS.md` will be created after the frontend scaffold exists and can be described accurately
- [x] Get user approval on the full plan before moving into implementation

### Quick status pass (today)
- Confirmed: user flow, learning loop, skill scope, child vs parent split, deterministic vs AI split, AGENTS documentation location decisions
- Confirmed: frontend high-level route map, initial backend API contract, initial database entity contract, and AI structured output contract details
- Pending before implementation: none

### Locked Part 1 contracts (MVP)

#### Initial frontend route map (high-level)

The route map is locked at a high level before scaffolding. Minor implementation-driven changes are allowed in Parts 2 and 3, but this is the intended structure:

- `/login`: sign-in screen for hardcoded credentials
- `/`: child home dashboard with mission card, progress highlights, and entry into practice
- `/activity/:activityId`: reading passage and question flow
- `/results/:sessionId`: post-submission feedback and celebration surface
- `/parent/progress`: parent-facing recent sessions and skill trend summary
- Optional UI surface for AI coach should be embedded in post-submission contexts (results and related follow-up views), not live during answering

#### Initial backend API surface (high-level)

Initial API contract for MVP implementation:

- `GET /api/health`
  - Returns service health for local/dev checks
- `POST /api/auth/login`
  - Validates hardcoded credentials `user` / `password`
  - Issues signed cookie session on success
- `POST /api/auth/logout`
  - Clears signed session cookie
- `GET /api/auth/session`
  - Returns signed-in state and minimal user/profile context
- `GET /api/dashboard`
  - Returns child dashboard state including mission and reward summary
- `GET /api/activities`
  - Returns list of available/recommended activities from seeded file-based content
- `GET /api/activities/{activity_id}`
  - Returns one activity with passage and questions
- `POST /api/activities/{activity_id}/submit`
  - Accepts responses, runs deterministic scoring and writing rubric, persists attempt/session/progress/reward updates
  - Returns scoring and feedback payload used by results screen
- `GET /api/progress/parent`
  - Returns parent summary (recent sessions, skill-tag trends, writing summary snippets)
- `POST /api/ai/coach`
  - Accepts post-submission context only
  - Returns validated structured coaching payload

#### Initial database entities (MVP persistence contract)

SQLite should persist operational data, not the seeded content library itself. Initial entities:

- `users`
  - MVP auth identity (starts with one hardcoded logical user, schema remains extensible)
- `child_profiles`
  - One child profile for MVP, linked to signed-in user
- `activity_sessions`
  - Attempt/session metadata per started or submitted activity
- `responses`
  - Stored multiple-choice selections and short-written responses
- `scores`
  - Deterministic scoring outputs, including short-writing rubric facets
- `progress_snapshots`
  - Aggregated completion and skill progress data used by dashboard and parent views
- `reward_state`
  - Stars/points/streaks/badges or equivalent lightweight motivational state
- `chat_messages`
  - AI coach request/response history tied to session and/or child profile

Seeded content remains file-based in MVP:
- Passage/question/activity definitions in local versioned files
- Skill tags and activity metadata in local versioned files

#### AI structured output contract (initial)

AI output must be schema-validated server-side and used only after answer submission in MVP.

Required response shape (initial contract):
- `message_to_child` (string)
- `celebration` (string)
- `explanation` (string)
- `next_step_suggestion` (string)
- `suggested_skill_tag` (string, optional)
- `suggested_next_activity_id` (string, optional)
- `message_to_parent` (string, optional)
- `confidence` (number in bounded range, e.g. 0 to 1)

Guardrails:
- Child-safe educational tone only
- No unrestricted chatbot behavior
- No live answer-assist while activity is in-progress
- Fallback response path required when schema validation fails

Testing expectations for this contract:
- Schema parsing/validation tests
- Invalid-output fallback tests
- Prompt-shaping tests that enforce post-submission context only
- Safety tests for age-appropriate and bounded role behavior

### Recommended MVP scope lock
- Child login using dummy credentials
- One child profile
- Seeded local activities from file-based content using a small passage library
- One daily mission or "practice now" flow
- Reading comprehension questions and short written responses
- Immediate deterministic scoring / feedback, including a simple deterministic rubric for short writing
- AI coach for post-submission explanation, encouragement, and optional next-step recommendation
- Parent progress page with recent activity and skill breakdown

### Tests
- [x] Planning review completed with no unresolved contradictions
- [x] Scope is small enough to implement locally without hidden platform work
- [x] Each later part has explicit success criteria

### Success criteria
- The user approves the plan
- The MVP scope is concrete, limited, and executable
- No major ambiguity remains around product shape or stack

---

## Part 2: Scaffolding and local runtime

### Goals
- Set up the Dockerized app skeleton
- Create backend and frontend directories
- Verify the project runs locally end to end

### Checklist
- [x] Create project directory structure: `frontend/`, `backend/`, `scripts/`, `docs/`
- [x] Create Dockerfile and any supporting config needed for local development
- [x] Set up FastAPI app in `backend/`
- [x] Set up a minimal NextJS app in `frontend/`
- [x] Add start / stop scripts for Mac, Windows, and Linux in `scripts/`
- [x] Build NextJS as a static export and serve the built assets from FastAPI at `/` (initial placeholder page is fine)
- [x] Add a simple backend API route such as `/api/health`
- [x] Verify the container builds and runs locally
- [x] Create `frontend/AGENTS.md` describing the scaffolded frontend structure and conventions

### Tests
- [x] Docker image builds successfully
- [x] App starts locally using the provided scripts
- [x] Visiting `/` returns a valid page
- [x] Calling `/api/health` returns a valid JSON response

### Success criteria
- The app can be started and stopped locally with a simple workflow
- Frontend and backend scaffolds exist and are wired together at a basic level
- `frontend/AGENTS.md` exists and accurately reflects the created scaffold

---

## Part 3: Build the child-friendly frontend shell

### Goals
- Replace the placeholder page with an actual reading-app shell
- Establish the visual system and navigation

### Checklist
- [x] Create a playful but readable design system for the MVP
- [x] Implement the login screen UI
- [x] Implement the child dashboard / mission home UI
- [x] Implement the activity screen layout
- [x] Implement the results / feedback screen layout
- [x] Implement the parent progress screen layout
- [x] Add a top-level app shell and navigation
- [x] Add placeholder data so the UI can be explored before backend wiring

### Tests
- [x] Frontend unit tests for key components
- [x] Frontend integration tests for route navigation and basic interactions
- [x] Visual checks for readability of passage text and question content

### Success criteria
- The app looks like a real product instead of a scaffold
- The key screens are navigable with mock data
- The design feels fun for a child without compromising readability

---

## Part 4: Add fake user sign in

### Goals
- Gate the experience behind a simple login
- Establish basic session behavior for local use

### Checklist
- [x] Implement login form using hardcoded credentials: `user` / `password`
- [x] Add backend login endpoint that validates hardcoded credentials and issues a signed session cookie
- [x] Add backend logout endpoint that clears the session cookie
- [x] Add backend session check endpoint or middleware for authenticated APIs/routes
- [x] Redirect logged-in users to the child dashboard
- [x] Add logout capability
- [x] Prevent unauthenticated access to the main app routes

### Tests
- [x] Successful login with correct credentials
- [x] Failed login with incorrect credentials
- [x] Authenticated users can access app screens
- [x] Logging out clears the session and returns to login
- [x] Missing or invalid session cookie is rejected consistently

### Success criteria
- Authentication works locally and is stable enough for MVP use
- The rest of the app can now assume a signed-in user context

---

## Part 5: Content model and seeded activity library

### Goals
- Create a small but useful library of local reading content
- Define the MVP content schema before persistence and APIs expand

### Checklist
- [x] Define a passage schema for literary and informational texts
- [x] Define a question schema for multiple-choice and written responses
- [x] Define skill tags for each activity
- [x] Create a small seeded content set appropriate for third grade
- [x] Keep seeded content in local files for MVP instead of storing the content library in SQLite
- [x] Ensure prompts and passages are child-safe and age-appropriate
- [x] Document the content model in `docs/`
- [x] Define a simple deterministic short-writing rubric (completion, relevance, sentence completeness, and feasible skill-specific checks)

### Tests
- [x] Seed content validates against the chosen schema
- [x] Activity screens can render all seeded passage and question types
- [x] No malformed or missing content fields in the initial set

### Success criteria
- The app has enough local content to demonstrate the full learning loop
- The content schema is explicit and easy to extend later

---

## Part 6: Database modeling

### Goals
- Design the local persistence layer for child progress and app state
- Keep the schema minimal and understandable

### Checklist
- [x] Propose the SQLite schema for the MVP
- [x] Decide which entities are stored relationally and which fields are stored as JSON
- [x] Include tables for users, child profile, sessions, responses, progress snapshots, rewards/streaks, and chat history as needed
- [x] Keep seeded activity/passage/question library file-based in MVP unless a later scope change requires DB storage
- [x] Document the database approach in `docs/`
- [x] Get user sign-off before deeper backend implementation

### Suggested data to persist
- User login identity
- Child profile basics
- Activity attempts and timestamps
- Answer selections / written responses
- Skill tags for completed activities
- Simple scores or completion markers
- Reward state such as stars, streaks, or badges
- AI conversation history tied to a session or child profile

### Tests
- [x] Schema can be created from scratch automatically
- [x] Seed data can be inserted successfully
- [x] Stored records support the expected queries for dashboard and progress views

### Success criteria
- The persistence model is approved and can support the MVP flow without rework
- The database can be created automatically on first run

---

## Part 7: Backend APIs for activities and progress

### Goals
- Implement the backend routes needed for a persistent local app
- Move core app state out of the frontend mocks

### Checklist
- [x] Add route to fetch the child dashboard state
- [x] Add route to list available or recommended activities
- [x] Add route to fetch a specific activity
- [x] Add route to submit responses for an activity
- [x] Add route to compute / return deterministic feedback for objective questions and short writing rubric checks
- [x] Add route to fetch parent progress summaries
- [x] Add route to fetch reward / streak state if kept separately
- [x] Create the SQLite DB automatically if it does not exist
- [x] Add backend validation for all request / response schemas

### Tests
- [x] Backend unit tests for scoring and persistence logic
- [x] API tests for each route
- [x] Invalid payloads return safe validation errors
- [x] Repeat submissions behave predictably

### Success criteria
- The backend can serve activities and store progress reliably
- The app has a clear, typed API contract for the main learning flow

---

## Part 8: Frontend + backend integration

### Goals
- Replace mock data with real backend data
- Make the app persist progress across reloads

### Checklist
- [x] Wire login flow to real auth/session handling used by the MVP
- [x] Load dashboard data from backend
- [x] Load activities from backend
- [x] Submit answers to backend
- [x] Show returned feedback and scores in the results screen
- [x] Update dashboard and progress views after completion
- [x] Ensure the app behaves correctly on refresh

### Tests
- [x] Integration tests covering sign in -> start activity -> submit -> view results -> view updated progress
- [x] Refresh persistence test
- [x] Empty-state test for a new user profile

### Success criteria
- The app behaves like a real persistent product instead of a demo
- A child can complete practice and see saved progress later

---

## Part 9: Reward loop and fun layer

### Goals
- Add the motivational layer that makes the app enjoyable for a 9-year-old
- Keep the reward system simple but visible

### Checklist
- [x] Add stars, points, streaks, badges, or another lightweight reward system
- [x] Show completion celebrations after activities
- [x] Add mission framing such as "today's quest" or "reading adventure"
- [x] Add clear positive reinforcement in child-facing copy
- [x] Ensure rewards are backed by persisted state where appropriate

### Tests
- [x] Reward values update correctly after activity completion
- [x] Streak logic behaves predictably
- [x] Reward UI updates after completion without manual refresh

### Success criteria
- The app feels substantially more engaging than a plain worksheet app
- The reward layer does not introduce complexity that breaks the core learning loop

---

## Part 10: AI connectivity via OpenRouter

### Goals
- Establish working OpenRouter integration in the backend
- Validate environment setup before deeper AI use

### Checklist
- [x] Add OpenRouter client configuration in the backend
- [x] Load `OPENROUTER_API_KEY` from environment
- [x] Use `openai/gpt-oss-120b` as the initial model
- [x] Add a simple backend route or test utility for connectivity
- [x] Validate the integration with a simple prompt such as `2+2`
- [x] Add safe logging and error handling

### Tests
- [x] Connectivity test succeeds when the key is present
- [x] Missing-key path fails cleanly with a clear error
- [x] Timeout or provider error path fails safely

### Success criteria
- OpenRouter connectivity is proven working from the local app
- The backend is ready to support constrained AI features

---

## Part 11: AI coaching contract and structured outputs

### Goals
- Turn the model into a constrained reading coach
- Keep the AI useful, predictable, and safe for a child-facing app

### Checklist
- [x] Define the system prompt for the AI coach role
- [x] Constrain the AI to child-safe educational behavior
- [x] Define a structured output schema for coaching responses
- [x] Include fields such as encouragement, explanation, hint, next-step suggestion, skill tags, and optional follow-up activity recommendation
- [x] Build backend validation for structured outputs
- [x] Add fallback behavior when the model returns invalid data
- [x] Keep AI memory limited to relevant session and progress context

### Example structured output fields
- `message_to_child`
- `message_to_parent` (optional)
- `hint`
- `explanation`
- `celebration`
- `suggested_next_activity_id` or `suggested_skill_tag`
- `writing_feedback`
- `confidence`

### Tests
- [x] Structured output parsing tests
- [x] Invalid schema fallback tests
- [x] Prompt construction tests
- [x] Safety tests for child-facing tone and bounded role behavior

### Success criteria
- The AI produces responses the backend can validate and safely display
- The AI behaves like a reading coach, not an unconstrained chatbot

---

## Part 12: Add the AI coach UI

### Goals
- Add a beautiful and useful child-friendly AI coach surface
- Allow the AI to support learning without taking over the core product loop

### Checklist
- [x] Add an AI coach sidebar, panel, or modal in the UI
- [x] Show post-submission explanations, encouragement, and follow-up suggestions
- [x] Allow the child or parent to ask limited questions about the current activity
- [x] Refresh the UI automatically when AI suggestions affect the next recommended activity or dashboard state
- [x] Keep the interface simple and non-overwhelming
- [x] Do not expose live hint-on-demand while the child is still answering in MVP

### Tests
- [x] Frontend tests for chat / coach widget rendering and interaction
- [x] End-to-end tests for asking for help during or after an activity
- [x] Tests for safe handling of backend AI errors

### Success criteria
- The AI coach feels helpful and delightful
- The core app still works well even if AI is temporarily unavailable

---

## Part 13: Parent progress view and simple skill reporting

### Goals
- Give the parent a practical view into progress without building a full analytics product
- Surface the data that matters most for early iteration

### Checklist
- [x] Show recent completed activities
- [x] Show completion count and simple trend information
- [x] Show basic strength / struggle areas by skill tag
- [x] Show recent writing feedback summaries where useful
- [x] Keep the page simple and understandable

### Tests
- [x] Parent view renders correctly for new and active users
- [x] Skill summaries reflect stored activity results accurately
- [x] No child-facing UI breaks when parent view is accessed

### Success criteria
- A parent can quickly understand what the child has practiced and where help may be needed
- The reporting stays lightweight and useful

---

## Part 14: Final polish and MVP hardening

### Goals
- Make the app stable enough to use regularly at home
- Remove obvious rough edges before expansion

### Checklist
- [x] Review copy for child-friendliness and clarity
- [x] Review reading passage typography for comfort and readability
- [x] Review API and schema consistency
- [x] Review error states and empty states
- [x] Review Docker and startup instructions
- [x] Confirm all major flows work from a clean local setup
- [x] Document known limitations and next-step ideas in `docs/`

### Tests
- [x] Full manual smoke test from fresh setup
- [x] Full automated test suite passes
- [x] Clean database creation path works
- [x] Existing database reuse path works

### Success criteria
- The MVP is pleasant, stable, and understandable
- The project is ready for real use and iteration with your daughter

---

## Part 15: Themed content expansion (50+ activities)

### Goals
- Expand the seeded activity library to at least 50 high-utility activities
- Organize content by explicit themes so discovery and mission selection are more useful

### Checklist
- [x] Add a required `theme` field to seeded activity schema
- [x] Add a difficulty tier (`easy`, `medium`, `difficult`) with good distribution across catalog activities
- [x] Add a centralized allowed theme list in seeded content files
- [x] Expand seeded content to 50+ activities with broad theme coverage
- [x] Add backend activity list filtering by theme
- [x] Add backend activity list filtering by difficulty
- [x] Return available theme metadata in activity listing responses
- [x] Add frontend theme + difficulty selectors and mission filtering on home screen
- [x] Keep scoring, submissions, and persistence contracts unchanged
- [x] Update docs for content and API contracts

### Tests
- [x] Backend API tests cover theme filter success and invalid theme handling
- [x] Frontend/unit tests assert 50+ seeded activities and broad theme coverage
- [x] End-to-end seeded-content test remains stable with expanded catalog
- [x] Full backend and frontend test suites pass

### Success criteria
- A signed-in child can access a large, themed activity catalog from home
- Mission selection is no longer limited to a fixed small set
- Expanded content remains schema-valid and deterministic-scoring compatible

---

## Explicit non-goals for MVP

These should not be built in the first version unless scope changes explicitly:
- True STAR score prediction or benchmark classification
- Large-scale adaptive assessment calibration
- Teacher / classroom multi-user workflows
- Admin dashboards
- Complex gamification economy
- Voice features
- Mobile apps
- Full production auth
- Broad open-ended chatbot behavior

---

## Stretch ideas after MVP

Only consider after the MVP is working well:
- Better adaptive difficulty selection
- More refined writing scoring
- Audio read-aloud support
- Vocabulary review loops and spaced repetition
- Richer parent controls and goals
- More polished avatars, worlds, or badge systems
- Explicit STAR-like practice mode with timed mini-checkpoints

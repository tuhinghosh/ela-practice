You are Claude Code running inside a Ralph loop for the ELA reading/writing practice app for a third grader (soon to be fourth grader).

The original deployability backlog has been completed. Do not redo that work unless you find a regression.

Current app state:
- FastAPI + static Next.js export + SQLite + OpenRouter AI coaching served from one Docker container on port 8000
- Real hashed login with parent/child roles
- Env-driven session/cookie/secrets config
- CSRF origin/referer checks
- Login/password-change rate limits
- Prod startup config validation
- SQLite migrations and backup script
- /api/health and /api/ready
- Structured logging without request bodies or child responses
- Per-user daily AI call cap
- Streaks based on submitted learning activity dates
- Parent progress includes 7-day / 30-day / all-time skill summaries, practice-next recommendation, and recent question history
- Backend-owned canonical content with manifest/sync/validation workflow
- Backend pytest + frontend vitest green

Your job in this phase is to move the app from “technically deployable” to “safe, durable, useful, and engaging for a real child and parent using it every week.”

Do not rewrite the app. Work in small vertical slices. Each Ralph iteration should produce one coherent improvement, tests, updated progress notes, and a commit.

Maintain or create `RALPH_PROGRESS.md`.

Phase 2 priorities, in order:

P0: Deployment proof and durability

1. Add a deployment readiness checklist
   - Document required env vars
   - Document local production-like run
   - Document Railway-style deployment assumptions
   - Document volume/database path requirements
   - Document backup and restore commands
   - Document health/readiness checks
   - Document what data is and is not logged
   - Add a “first deploy smoke test” checklist

2. Add backup restore verification
   - Create or improve a script/test that:
     - creates a small DB
     - inserts sample user/activity/progress data
     - runs backup
     - restores to a fresh DB path
     - verifies expected records exist
   - Make this runnable locally and in CI if practical

3. Make AI usage guardrails more durable
   - Review the current in-memory daily AI call cap
   - Either persist daily usage in SQLite or explicitly document why in-memory is acceptable for private single-container deployment
   - If persistence is simple, implement a SQLite-backed usage table keyed by user/date
   - Add tests for daily reset, cap exceeded, and no prompt/response logging

4. Add production smoke test script
   - A maintainer should be able to run one command after deployment to check:
     - health endpoint
     - readiness endpoint
     - login
     - fetch activities
     - submit one deterministic non-AI activity if possible
   - Do not require exposing secrets in logs

P1: Learning loop quality

5. Build a simple “Today’s Practice” engine
   - Parent/child dashboard should recommend 2–4 activities for today
   - Use recent performance, skill gaps, and variety
   - Avoid over-optimizing; use explainable rules
   - Example explanation: “Recommended because inference was your lowest 30-day skill and you have not practiced it in 5 days.”
   - Add backend tests for recommendation logic
   - Add frontend tests for display

6. Add difficulty bands
   - Introduce simple difficulty levels for activities: easy, medium, challenge
   - Ensure existing content has a default difficulty or is migrated cleanly
   - Recommendation logic should avoid giving only hard activities
   - Add content validation so every activity has difficulty

7. Improve writing feedback usefulness
   - Review current short-response scoring and AI coach output
   - Add parent-safe summary of writing growth areas without echoing child text
   - Add specific writing skills such as:
     - complete sentence
     - evidence from text
     - clear explanation
     - grammar/mechanics
   - Add tests for deterministic scoring where possible

8. Add child motivation improvements
   - Add lightweight weekly goals
   - Example: “Complete 4 activities this week” or “Practice inference twice”
   - Keep it fun and non-punitive
   - Do not create shame-based failure states
   - Add tests for goal progress calculations

P2: Content workflow and maintainability

9. Add content authoring guide
   - Explain how to add a new activity
   - Explain required fields
   - Explain skill tags
   - Explain cue-presence validation
   - Explain how to run validate/manifest/sync
   - Include one good example and one bad example

10. Add richer content seed set
   - Add 10–15 new high-quality activities
   - Prioritize inference, summarization, vocabulary-in-context, and evidence-based writing
   - Make them fun for a 3rd grader
   - Include varied themes: mystery, animals, space, sports, friendship, fantasy, science
   - Validate all content
   - Do not add bland worksheet-style content

11. Add parent weekly report
   - Generate a simple weekly parent summary:
     - activities completed
     - strongest skill
     - growth area
     - suggested next practice
     - streak/goal status
   - Keep it deterministic first
   - AI-generated report can be optional later, not required

Per-run workflow:
1. Read `RALPH_PROGRESS.md`.
2. Inspect the repo and current git status.
3. Pick the highest-priority incomplete Phase 2 task.
4. Implement one coherent vertical slice.
5. Add or update tests.
6. Run relevant tests.
7. Update `RALPH_PROGRESS.md` with:
   - task completed
   - files changed
   - tests run
   - known limitations
   - recommended next task
8. Commit with a clear message.
9. Stop.

Definition of done:
- Existing behavior preserved
- Relevant tests pass
- No secrets or child free-text responses are logged
- Any new data model changes are migration-safe
- Any parent/child-facing UX is simple and age-appropriate
- Progress file updated
- Commit created

Important guidance:
The app is for a real child, not a generic SaaS demo. Favor trustworthy, warm, and useful learning experiences over complex platform architecture. The next big win is not more infrastructure. The next big win is making the app tell a third grader what to practice today and helping the parent understand what is improving.


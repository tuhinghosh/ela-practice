# The Reading and Writing Adventure MVP web app

## Business Requirements

This project is building a fun local MVP that a third-grade child can use to strengthen reading and writing skills.

Key product goals:
- Make daily practice feel playful, encouraging, and rewarding
- Help a child practice third-grade reading comprehension, vocabulary, and written responses
- Build toward the kinds of skills measured by STAR Reading over time
- Give the parent a simple way to see recent progress and areas of strength or struggle

Key MVP features:
- A user can sign in
- When signed in, the user sees a child-friendly home screen with a clear "today's mission"
- The child can complete short reading activities using both literary and informational passages
- The child can answer multiple-choice and short written-response questions
- The child receives immediate, supportive feedback
- The app stores progress locally so completed work and streaks persist across sessions
- There is an AI chat / coaching feature that can explain mistakes, give hints, and celebrate wins
- The AI can optionally generate a follow-up activity or revise the next prompt based on recent performance
- A simple parent-facing progress view shows recent sessions, skill tags, and basic trends

## Learning Scope for MVP

The MVP should focus on a narrow, high-value set of third-grade literacy skills.

Initial skill areas:
- Reading comprehension for short literary passages
- Reading comprehension for short informational passages
- Main idea and supporting details
- Inference with textual evidence
- Sequence / summarization
- Vocabulary in context
- Sentence-level writing quality
- Short paragraph responses to prompts

The skill scope above is chosen to align with the broad areas described in the attached STAR Reading overview, including literature, informational text, and language / vocabulary domains.

## Product Principles

1. Fun first
   - The app must feel inviting, colorful, and game-like without becoming noisy or distracting.
   - The child should feel successful often.
   - Feedback should be warm, specific, and motivating.

2. Short sessions
   - Core activities should be completable in 5 to 10 minutes.
   - Every screen should make it obvious what to do next.

3. Low friction
   - Avoid complicated setup, long forms, and too many navigation choices.
   - The MVP should be easy for a parent to run locally.

4. Real learning value
   - Activities should target concrete reading and writing skills.
   - Feedback should be useful, not generic praise.

5. Safe and age-appropriate
   - Content must stay firmly within child-safe, school-appropriate topics and language.
   - The AI should be constrained to act like a reading coach, not a free-form chatbot.

## Limitations

For the MVP, there will only be a user sign in hardcoded to `user` and `password`, but the database should support multiple users in the future.

For the MVP, there will only be one child profile and one parent view for the signed-in user.

For the MVP, the content library can be small and seeded locally.

For the MVP, only English content is required.

For the MVP, the app will run locally in Docker.

For the MVP, the app does not need full STAR score prediction, benchmarking, or true assessment calibration. It only needs to build toward relevant skills and produce simple local progress signals.

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at `/`
- Everything packaged into a Docker container
- Use `uv` as the Python package manager inside the Docker container
- Use OpenRouter for AI calls. An `OPENROUTER_API_KEY` is in `.env` in the project root
- Use `openai/gpt-oss-120b` as the model unless explicitly changed later
- Use SQLite local database, creating a new DB if it does not exist
- Start and stop server scripts for Mac, Windows, and Linux in `scripts/`
- Frontend will communicate with backend over JSON APIs
- AI features should use structured outputs so the backend can safely validate and apply AI-generated results

## Starting Point

There is no working frontend or backend for this reading app yet.

The project should start from scratch while preserving the same stack and local Docker workflow used for the Kanban example.

Because there is no existing frontend code to document, the initial implementation should create a `frontend/AGENTS.md` file only after the frontend scaffold exists. That file should then describe the actual frontend structure, routes, components, state management choices, and testing approach.

## Initial User Experience Vision

The MVP should feel like a light learning game rather than a school worksheet.

Target UX elements:
- A cheerful landing / login screen
- A child dashboard with a mascot or playful theme
- A clear mission card such as "Read this story" or "Help the explorer solve today's reading quest"
- Progress indicators such as stars, streaks, badges, or treasure pieces
- Short celebrations after finishing an activity
- Encouraging feedback that explains what was good and what to improve next
- A parent summary page that is simple and useful, not overloaded

## Suggested Information Architecture

Core screens for MVP:
- Login
- Child home / mission dashboard
- Reading activity screen
- Results / feedback screen
- Parent progress screen
- AI coach sidebar or panel

## Proposed Core Domain Objects

The codebase will likely need models similar to the following:
- User
- ChildProfile
- Activity
- Passage
- Question
- Session
- Response
- SkillTag
- ProgressSnapshot
- ChatMessage
- RewardState

These may evolve during implementation, but the MVP should keep the schema small and understandable.

## Testing Expectations

The project should include both backend and frontend tests.

Minimum expectations:
- Backend unit tests for models, scoring rules, prompt building, and API routes
- Frontend component tests for key screens and interactions
- Integration tests for sign in, launching an activity, submitting answers, viewing feedback, and viewing saved progress
- AI integration tests should validate structured outputs and safe fallbacks when model responses are invalid

## Color and Design Direction

The app should be brighter and more playful than the Kanban app while still readable.

Suggested direction:
- Warm yellow or gold for rewards / stars
- Bright blue for primary UI surfaces
- Purple or magenta for playful action buttons
- Deep navy for headings and readable text anchors
- Soft neutral backgrounds to keep reading passages easy on the eyes

Important:
- Reading areas must prioritize legibility over decoration
- Avoid clutter and animation overload
- Keep passage text high contrast and comfortably spaced

## Coding Standards

1. Use current stable libraries and idiomatic patterns
2. Keep it simple. Do not over-engineer. Build the smallest thing that works well.
3. Optimize for clarity and maintainability over cleverness
4. Keep the README minimal and practical
5. When something breaks, identify root cause before attempting a fix. Do not guess.
6. Keep AI integration constrained and schema-driven
7. Prefer deterministic local content and logic for the base learning loop; use AI where it adds clear value
8. Child-facing copy must be warm, encouraging, and age-appropriate

## Working Documentation

All planning and execution documents for this project should live in the `docs/` directory.

Before implementing a phase of work:
- Review `docs/PLAN.md`
- Confirm the current phase, tests, and success criteria
- Update progress in the checklist as work is completed

Any major change in product scope, schema, API contract, or AI contract should be documented before implementation proceeds.

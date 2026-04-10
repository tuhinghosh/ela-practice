# Frontend implementation guide

This document describes the current frontend scaffold and how to work within it during the MVP.

## Current stack

- NextJS app router
- TypeScript
- ESLint
- Static export mode (`next build` outputs static files for FastAPI to serve)

## Current structure

- `src/app/layout.tsx`: top-level HTML shell and metadata
- `src/app/page.tsx`: child dashboard / mission home (backend API powered with local fallback)
- `src/app/login/page.tsx`: login screen shell
- `src/app/activity/[activityId]/page.tsx`: static wrapper for activity route params
- `src/app/activity/[activityId]/activity-client.tsx`: activity UI with backend fetch + submit
- `src/app/results/[sessionId]/page.tsx`: static wrapper for results route params
- `src/app/results/[sessionId]/results-client.tsx`: results UI with backend fetch, reward celebration, and AI coach interaction
- `src/app/parent/progress/page.tsx`: parent-facing progress summary from backend with trend, skill summary, and writing highlights
- `src/app/screens.module.css`: shared screen/card styles for MVP shell
- `src/app/globals.css`: global styles
- `src/components/app-shell.tsx`: shared app shell and top-level navigation
- `src/components/app-shell.module.css`: shell/header/navigation styles
- `src/components/button.tsx`: shared button primitives with tone variants (`primary`, `secondary`, `ghost`)
- `src/components/card.tsx`: shared card wrapper primitive
- `src/components/tag.tsx`: shared tag/chip primitive
- `src/components/layout.tsx`: shared layout utilities (`Stack`, `Split`, `StatGrid`)
- `src/components/ai-coach-panel.tsx`: post-submission coach panel with limited question input
- `src/content/activities.json`: file-based seeded activities for MVP
- `src/content/skill-tags.json`: allowed skill tag list for seeded content
- `src/content/themes.json`: allowed theme list for seeded activities and theme browsing
- `src/lib/content-schema.ts`: frontend runtime validation and typed parsing for seeded content
- `src/lib/mock-data.ts`: app-facing exports combining seeded content and placeholder progress data
- `src/lib/api.ts`: typed backend API client for dashboard, activities, submission, results, and progress
- `next.config.ts`: NextJS config, including static export settings
- `vitest.config.ts` and `vitest.setup.ts`: unit/component test setup
- `playwright.config.ts`: E2E test setup

## Route conventions (high-level)

- `/login`: login screen
- `/`: child dashboard (home)
- `/activity/:activityId`: reading activity flow
- `/results/:sessionId`: post-submission feedback
- `/parent/progress`: parent progress view

Part 8 integrates these screens with backend APIs while keeping fallback data for frontend-only development mode.

## Themed activity browsing

- Home screen supports selecting a theme and filtering available activities.
- Activity list API returns both `activities` and `themes`.
- Mission selection can be set from the available activity list without changing backend submission flow.

## Reward loop behavior (Part 9)

- Reward tracker shows stars, points, streak, and badges
- Submission returns a reward snapshot with stars/points earned and new badges
- Results screen surfaces a post-activity celebration using the persisted reward snapshot

## AI coach UI behavior (Part 12)

- AI coach appears on results/post-submission only
- Child/parent can ask limited follow-up questions about the completed activity
- Coach suggestions can set a suggested next activity, reflected on mission home
- UI handles AI/backend failures safely without breaking the core flow

## Auth behavior (Part 4)

- Login page calls backend auth endpoints (`/api/auth/login`, `/api/auth/session`)
- Top navigation includes a logout action that calls `/api/auth/logout`
- Backend middleware protects app routes and redirects unauthenticated users to `/login`
- Credentials remain fixed to `user` / `password` for MVP

## State management approach (MVP direction)

- Keep state local and simple in early phases
- Prefer component state and small utility helpers before introducing heavier abstractions
- Move durable state to backend APIs once integration phase begins

## Testing approach (locked)

- Unit/component tests: `vitest` + React Testing Library
- End-to-end/integration tests: `playwright`

## Styling guidance

- Keep child-facing UI playful but readable
- Prioritize legibility for reading content over decorative effects
- Follow the product colors and tone defined in root `AGENTS.md`

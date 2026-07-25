# MVP content model

This document defines the file-based seeded content model for MVP Part 5.

## Seed file locations

- `backend/content/activities.json` (canonical)
- `backend/content/skill-tags.json` (canonical)
- `backend/content/themes.json` (canonical)
- `backend/content/review-status.json` (canonical editorial status registry)
- `frontend/src/content/` contains the build-time mirror maintained by the content sync workflow

Seeded content remains in local versioned files for MVP and is not stored as the source-of-truth library in SQLite.

## Activity schema

Each activity entry contains:

- `id` (string, unique)
- `title` (string)
- `theme` (string, one of the allowed values in `themes.json`)
- `difficulty` (optional string, one of `easy`, `medium`, `difficult`; defaults are assigned deterministically if omitted)
- `passageType` (`literary` or `informational`)
- `missionLabel` (string)
- `passageTitle` (string)
- `passageText` (string)
- `questions` (array, at least 2 items)
- `skillTags` (array, at least 1 tag)
- `sourceUrls` (optional array of factual-review sources; required by the pilot harness for informational pilot activities)

## Question schema

Each question entry contains:

- `id` (string)
- `type` (`multiple-choice` or `short-response`)
- `prompt` (string)
- `choices` (required for `multiple-choice`, omitted for `short-response`)
- `correctChoice` (required for `multiple-choice`, omitted for `short-response`)
- `skillTag` (optional during legacy-content migration; identifies the one primary skill measured by the question)

Validation constraints:

- Multiple-choice items require at least two choices
- Short-response items must not include choice arrays
- Activity IDs must be unique
- Skill tags must come from the allowed list
- A question-level `skillTag`, when present, must also appear in its activity's `skillTags`

## Skill evidence and migration rule

Skill reporting is based on question-level evidence, not the activity's overall
score. Questions with an explicit `skillTag` contribute only to that skill's
score. Untagged legacy questions are reported under `overall-reading`; the app
must not copy an overall activity percentage onto every activity tag. This
allows existing content to remain usable while reviewed activities are tagged
gradually.

Only activities where every question has a `skillTag` are eligible for
adaptive selection. See `docs/ADAPTIVE_RECOMMENDATIONS.md` for the selection
rules and thresholds.

## Skill tag schema

Allowed MVP tags are defined in `backend/content/skill-tags.json`:

- `reading-comprehension`
- `main-idea`
- `inference`
- `sequence`
- `summary`
- `vocabulary`
- `sentence-quality`
- `short-writing`

## Theme schema

Allowed MVP content themes are defined in `frontend/src/content/themes.json`:

- `nature`
- `space`
- `community`
- `sports`
- `mystery`
- `history`
- `ocean-weather`
- `arts`
- `friendship`
- `logic`

## Difficulty schema

Allowed difficulty tiers:

- `easy`
- `medium`
- `difficult`

## Passage length guidance

- Child-facing reading passages should render at roughly 10 to 15 sentences for consistent practice depth.
- Non-poetry passages that fail the minimum structural checks are rejected during content validation; the app does not pad or rewrite them at load time.

## Deterministic short-writing rubric (MVP v1)

Short written responses are scored deterministically first using lightweight rubric checks:

- `completion`: student submitted a non-empty response
- `relevance`: response includes topic-aligned terms from prompt/passage
- `sentence_completeness`: response includes at least one complete sentence marker
- `skill_specific_checks`: small rule-based checks by skill focus where feasible (for example, evidence language for inference or concise gist for summary)

AI coaching may explain and encourage after submission, but does not replace deterministic scoring in MVP v1.

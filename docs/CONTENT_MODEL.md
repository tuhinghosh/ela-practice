# MVP content model

This document defines the file-based seeded content model for MVP Part 5.

## Seed file locations

- `frontend/src/content/activities.json`
- `frontend/src/content/skill-tags.json`
- `frontend/src/content/themes.json`

Seeded content remains in local versioned files for MVP and is not stored as the source-of-truth library in SQLite.

## Activity schema

Each activity entry contains:

- `id` (string, unique)
- `title` (string)
- `theme` (string, one of the allowed values in `themes.json`)
- `passageType` (`literary` or `informational`)
- `missionLabel` (string)
- `passageTitle` (string)
- `passageText` (string)
- `questions` (array, at least 2 items)
- `skillTags` (array, at least 1 tag)

## Question schema

Each question entry contains:

- `id` (string)
- `type` (`multiple-choice` or `short-response`)
- `prompt` (string)
- `choices` (required for `multiple-choice`, omitted for `short-response`)

Validation constraints:

- Multiple-choice items require at least two choices
- Short-response items must not include choice arrays
- Activity IDs must be unique
- Skill tags must come from the allowed list

## Skill tag schema

Allowed MVP tags are defined in `frontend/src/content/skill-tags.json`:

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

## Deterministic short-writing rubric (MVP v1)

Short written responses are scored deterministically first using lightweight rubric checks:

- `completion`: student submitted a non-empty response
- `relevance`: response includes topic-aligned terms from prompt/passage
- `sentence_completeness`: response includes at least one complete sentence marker
- `skill_specific_checks`: small rule-based checks by skill focus where feasible (for example, evidence language for inference or concise gist for summary)

AI coaching may explain and encourage after submission, but does not replace deterministic scoring in MVP v1.

# Transparent adaptive recommendations

## Purpose

The recommendation system chooses one next activity using stored,
question-level skill evidence. It is intentionally a small rules engine, not a
prediction model or a recreation of Renaissance STAR's proprietary adaptive
assessment.

## Evidence

Each submitted response stores two values in `responses.evidence_json`:

- `skill_tag`: the question's one primary measured skill
- `score_percent`: the deterministic score for that response

The 30-day skill window aggregates these response-level observations. Older
sessions that predate question evidence remain readable through their stored
session-level skill breakdown.

## Flexible starter phase

The first three distinct reviewed activities establish enough initial evidence
to begin adaptation. There is no fixed starter path. Any reviewed activity
counts toward the three-activity starter phase.

While fewer than three reviewed activities are complete, the system suggests
an uncompleted easy reviewed activity, preferring the current easy mystery
on-ramp. The older Paw Prints pilot receives no starter priority. The child can
accept that suggestion, ask to see another, filter the reviewed library, or
start any reviewed activity directly. Recommendations are guidance, never
prerequisites.

## Decision rule

For the selected skill in the 30-day window:

- Fewer than 3 observations: gather more evidence; do not change difficulty
- At least 3 observations and average below 60%: choose easier practice
- Average from 60% through 85%: hold at the current practice level
- Average above 85%: choose a harder challenge

Skills needing a step down are handled first, followed by skills needing more
evidence, skills in the productive range, and skills ready to step up.

## Activity eligibility

An activity can appear in the child chooser or be selected adaptively only when
it is editorially reviewed. Adaptive candidates must also have every question
declare its primary `skillTag`. This prevents draft or legacy activities from
becoming child-facing practice or claiming targeted evidence.

Within eligible activities, selection prefers:

1. An activity not previously completed
2. Difficulty closest to the rule's target difficulty
3. Stable activity ID order as a deterministic tie-breaker

## Visibility

The child dashboard shows why the recommended mission was chosen. The parent
view shows the phase, decision, target skill, observation count, average,
difficulty, reason, and exact threshold rule.

## Current scope

The reviewed pool contains 42 activities, including 18 easy activities and a
six-activity easy mystery on-ramp. Every core adaptive skill has eligible
coverage at each difficulty; content tests enforce that coverage.

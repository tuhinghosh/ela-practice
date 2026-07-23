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

## Baseline gate

The three reviewed pilot activities run in this order before adaptation:

1. The Case of the Library Paw Prints
2. A Day Called a Sol
3. Japan: One Country, Many Islands

This produces initial evidence across the current core skills. Until all three
are complete, the next unfinished pilot is the recommendation.

## Decision rule

For the selected skill in the 30-day window:

- Fewer than 3 observations: gather more evidence; do not change difficulty
- At least 3 observations and average below 60%: choose easier practice
- Average from 60% through 85%: hold at the current practice level
- Average above 85%: choose a harder challenge

Skills needing a step down are handled first, followed by skills needing more
evidence, skills in the productive range, and skills ready to step up.

## Activity eligibility

An activity can be selected adaptively only when every question explicitly
declares its primary `skillTag`. This prevents legacy activities from claiming
targeted learning evidence they were not authored to measure.

Within eligible activities, selection prefers:

1. An activity not previously completed
2. Difficulty closest to the rule's target difficulty
3. Stable activity ID order as a deterministic tie-breaker

## Visibility

The child dashboard shows why the recommended mission was chosen. The parent
view shows the phase, decision, target skill, observation count, average,
difficulty, reason, and exact threshold rule.

## Current limitation

The reviewed pool contains nine activities: the three starter missions plus
six adaptive missions spanning animals, friendship, the human body, board-game
design, space science, and world geography. Every core adaptive skill has at
least one eligible easy, medium, and difficult activity; a content test enforces
that coverage.

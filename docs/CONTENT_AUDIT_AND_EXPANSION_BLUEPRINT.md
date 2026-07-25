# Content audit and expansion blueprint

**Audit date:** 2026-07-24

**Repository baseline:** `25789d0`

**Canonical content version:** `1.2.0`

## Purpose

Build a reviewed, engaging content library that can support transparent
question-level adaptation for a rising fourth grader. The app should practice
skills relevant to STAR Reading and selective-school reading work without
claiming to reproduce Renaissance's calibrated assessment or predict a STAR
score.

The canonical content source is `backend/content/`. The frontend copy is a
generated mirror and is not audited separately.

## Executive finding

The library contains 88 structurally valid activities, but it does not yet
contain 88 equally usable adaptive activities.

| Cohort | Count | Current use |
|--------|------:|-------------|
| Reviewed and adaptation-eligible | 9 | Keep and improve |
| Confirmed boilerplate rewrite required | 26 | Exclude from reviewed pool until rewritten |
| Legacy migration and editorial review required | 53 | Keep as optional variety; migrate or retire |

The next product goal is a **36-activity reviewed adaptive core**, with 12
activities at each difficulty tier. The 79 legacy activities should not be
treated as skill-specific adaptive evidence until they have explicit
difficulty, question tags, explanations, guidance, and editorial approval.

## Audit method

The audit combined:

- canonical schema and manifest validation;
- counts by theme, genre, difficulty, question type, and skill;
- question-level adaptation eligibility;
- answer-position and repeated-language heuristics;
- source coverage for informational passages;
- review of runtime fallback and recommendation behavior;
- comparison with Renaissance's published description of STAR Reading skill
  areas.

Structural validation passes:

```text
ok: 88 activities, 13 themes, manifest version=1.2.0
```

Structural validity is necessary but does not establish editorial quality,
factual accuracy, calibrated difficulty, or useful adaptive evidence.

## Existing-library audit

### Inventory

| Measure | Result |
|---------|--------|
| Activities | 88 |
| Questions | 328 |
| Multiple choice | 240 |
| Short response | 88 |
| Literary passages | 33 |
| Informational passages | 45 |
| Poetry passages | 10 |
| Passage words | 122–398; median 248 |
| Explicit difficulty | 9 activities |
| Explicit question skill tags | 36 questions |
| Untagged questions | 292 |

Theme coverage is highly uneven:

| Theme | Activities |
|-------|-----------:|
| Space | 10 |
| Community | 9 |
| Friendship | 9 |
| Mystery | 9 |
| Arts | 8 |
| History | 8 |
| Logic | 8 |
| Nature | 8 |
| Ocean/weather | 8 |
| Sports | 8 |
| Animals | 1 |
| Human body | 1 |
| World geography | 1 |

`pilot-world-japan-01` is geographically focused but is currently tagged
`community`, so the practical geography count is two and the taxonomy should
be corrected during migration.

### Adaptation integrity

The runtime assigns missing difficulty by sorting activity IDs and rotating
through `easy`, `medium`, and `difficult`. This produces balanced counts but
does not measure text or item difficulty.

Untagged questions are stored as `overall-reading`. Activity-level tags do not
become question-level evidence. The recommendation selector requires every
question in a candidate activity to have an explicit tag, so only nine
activities currently form the meaningful adaptive pool.

Reviewed question-skill coverage:

| Skill | Easy | Medium | Difficult |
|-------|-----:|-------:|----------:|
| Inference | 3 | 3 | 3 |
| Main idea | 1 | 2 | 2 |
| Reading comprehension/key details | 3 | 2 | 1 |
| Sequence | 1 | 1 | 0 |
| Summary | 2 | 2 | 3 |
| Vocabulary | 2 | 2 | 3 |

There is no question-level adaptive evidence for `short-writing` or
`sentence-quality`. Written responses currently combine a reading objective
and writing quality, but the schema permits only one primary question tag.

### Editorial and item-quality findings

1. **Confirmed repeated filler**

   - Nineteen passages repeat: “Scientists noticed that this subject needed
     more study.”
   - Seven passages repeat: “These findings improved how people understood the
     subject.”

   These sentences occur across unrelated topics and should trigger mandatory
   rewriting, not simple deletion, because surrounding transitions may rely on
   them.

2. **Correct-answer position bias**

   In the legacy multiple-choice set, 170 of 213 correct answers are in
   position two. A child could exploit answer location rather than read the
   passage. The reviewed cohort is better but still uneven.

3. **Generic question repetition**

   Main-idea, theme, and author-purpose prompts are repeated with minimal
   variation across many passages. Reusing a skill is desirable; reusing an
   item shell without passage-specific reasoning is not.

4. **Missing feedback**

   The 292 legacy questions have no answer explanations or written-response
   guidance. The reviewed set has explanations for its 27 multiple-choice
   questions and guidance for its nine written responses.

5. **Missing factual provenance**

   Thirty-nine legacy informational passages have no source URLs. Six reviewed
   informational activities cite 11 sources. Informational content should be
   checked against authoritative sources before being placed in the reviewed
   pool.

6. **Difficulty is not calibrated**

   The nine reviewed labels show a sensible increase in longer vocabulary, but
   passage length and sentence length overlap heavily. Difficulty must include
   item reasoning, evidence distance, text structure, vocabulary support, and
   distractor plausibility—not word count alone.

7. **Interest mismatch**

   The library has strong general breadth but little reviewed depth in Reyana's
   highest-interest areas: cats and dogs, the human body, countries and maps,
   school/teacher situations, and board games. Space has the best coverage.

8. **Skill taxonomy gap**

   Renaissance describes vocabulary, comprehension/constructing meaning,
   literary text, author's craft, and argument evaluation. The current library
   covers several foundational comprehension skills but has no explicit
   author-craft, text-structure, compare-texts, or claim/evidence tags.

Official context:

- https://www.renaissance.com/products/assessment/star-assessments/star-reading/
- https://star-help.renaissance.com/hc/en-us/articles/12542471051803-Star-Assessments-for-Reading-Technical-Manual

## Complete disposition

### Keep in the reviewed adaptive pool

- `pilot-space-mars-01`
- `pilot-mystery-cat-01`
- `pilot-world-japan-01` — move to `world-geography`
- `adaptive-animals-dog-signals-01`
- `adaptive-friendship-lunch-table-01`
- `adaptive-body-sleep-cycles-01`
- `adaptive-logic-game-testers-01`
- `adaptive-space-exoplanet-shadow-01`
- `adaptive-world-brazil-map-01`

These activities should still receive periodic fact, source, and child-appeal
review. “Reviewed” means suitable for the current pilot, not permanently
finished.

### Rewrite before migration

Confirmed repeated boilerplate appears in:

- Arts: `arts-03`, `arts-06`, `arts-07`
- Community: `community-01`, `community-02`, `community-03`, `community-05`,
  `community-06`, `community-07`
- Friendship: `friendship-04`, `friendship-06`, `friendship-07`
- Logic: `logic-01`, `logic-02`, `logic-04`, `logic-05`, `logic-06`
- Mystery: `mystery-06`
- Nature: `nature-04`, `nature-05`, `nature-07`
- Ocean/weather: `ocean-weather-04`, `ocean-weather-05`,
  `ocean-weather-07`
- Space: `space-06`
- Sports: `sports-01`

Each rewrite must recheck the full passage, questions, correct answers,
distractors, difficulty, sources, and feedback. Do not patch only the repeated
sentence.

### Migrate or retire after editorial review

- Arts: `arts-01`, `arts-02`, `arts-04`, `arts-05`, `arts-08`
- Community: `community-04`, `community-08`
- Friendship: `friendship-01`, `friendship-02`, `friendship-03`,
  `friendship-05`, `friendship-08`
- History: `history-01` through `history-08`
- Logic: `logic-03`, `logic-07`
- Mystery: `mystery-01` through `mystery-05`, `mystery-07`, `mystery-08`
- Nature: `nature-01`, `nature-02`, `nature-03`, `nature-06`, `nature-08`
- Ocean/weather: `ocean-weather-01`, `ocean-weather-02`,
  `ocean-weather-03`, `ocean-weather-06`, `ocean-weather-08`
- Space: `space-01` through `space-05`, `space-07`, `space-08`
- Sports: `sports-02` through `sports-08`

Migration is not automatic preservation. Retire an activity when it is
redundant, dull, factually fragile, culturally shallow, or more expensive to
repair than replace.

## Target reviewed library

### Size and coverage gate

Target 36 reviewed activities:

- 12 easy;
- 12 medium;
- 12 difficult;
- at least four usable activities for each core reading skill at every tier;
- at least 40% literary and 40% informational overall;
- poetry and paired texts as supplementary formats;
- no theme supplies more than 20% of the adaptive pool.

The initial core skills remain:

- key details / reading comprehension;
- main idea;
- inference with evidence;
- sequence;
- summary;
- vocabulary in context.

A later schema milestone should add:

- author's purpose and craft;
- text structure;
- compare and contrast across texts;
- claim, reason, and evidence.

Writing evidence should be modeled separately from the primary reading skill:

- relevance to the prompt;
- use of textual evidence;
- sentence completeness and quality;
- organization and clarity.

Do not force a written summary question to choose between a `summary` tag and a
`sentence-quality` tag.

### Interest and awareness mix

The 36-activity reviewed core should approximately include:

| Interest family | Target | Direction |
|-----------------|-------:|-----------|
| Countries, maps, and world geography | 7 | Continents, scale, climate, daily life, connections between places |
| Cats, dogs, and animal behavior | 5 | Communication, senses, care, adaptation, working animals |
| School, friends, and teachers | 5 | Lunchroom, projects, misunderstandings, fairness, collaboration |
| Space and astronomy | 4 | Planets, missions, observation, current science |
| Human body and health science | 4 | Sleep, senses, muscles, digestion, immune response |
| Logic, puzzles, and board games | 4 | Rules, strategy, testing, probability language, fair play |
| Mystery and investigation | 4 | Evidence, competing explanations, observation, inference |
| Arts and performance fantasy | 3 | Original pop groups, rehearsal, stagecraft, folklore-inspired adventure |

Pop-culture energy may inspire tone and stakes, but passages must use original
characters, worlds, plots, and lyrics. Do not reproduce or closely imitate
copyrighted franchises such as *KPop Demon Hunters*.

Geography content must build connected knowledge rather than isolated trivia.
Include maps, neighboring regions, climate, language context, food or school
life, and respectful comparisons without presenting one child as a
representative of an entire country.

## Difficulty standard

Keep most passages within the currently successful 170–280 word range.
Difficulty is primarily controlled by reasoning demand:

### Easy

- mostly explicit evidence in one paragraph;
- concrete vocabulary with strong context;
- one-step inference;
- clearly distinct distractors;
- short response can be answered with one supported idea.

### Medium

- evidence may span two paragraphs;
- vocabulary requires context plus word-part or contrast clues;
- sequence may include cause/effect rather than simple chronology;
- distractors are plausible but contradicted by the text;
- short response requires a claim and at least one detail.

### Difficult

- integrates details across the passage or two short texts;
- distinguishes main idea from an attractive supporting detail;
- interprets author choice, text structure, or claim/evidence;
- uses nuanced vocabulary that remains inferable;
- distractors represent realistic reasoning errors;
- short response requires a concise claim with two connected details.

Difficulty labels remain editorial until Reyana produces enough question-level
evidence. Later adjustments should be based on observed success, response time,
and error patterns—not on a claimed STAR scale.

## Activity and item contract

Every reviewed activity must include:

- explicit difficulty;
- one primary theme and passage type;
- four questions: three multiple choice and one constructed response;
- an explicit primary skill tag on every question;
- an answer explanation for every multiple-choice item;
- response guidance for every constructed response;
- authoritative source URLs for informational claims;
- original, child-safe writing;
- a passage-specific mission label;
- an editorial review record.

Multiple-choice requirements:

- four choices unless a documented item design requires three;
- one unambiguously best answer;
- plausible distractors tied to common misreadings;
- no “all of the above” or trick wording;
- correct-answer positions balanced across each batch;
- no predictable repeated answer-position sequence;
- choices parallel in grammar and approximate length.

Constructed-response requirements:

- asks for textual evidence, not personal disclosure;
- can be answered from the passage;
- defines what a complete response contains;
- receives separate reading-objective and writing-quality evidence.

## Authoring and review loop

1. Select a cell from the topic × genre × difficulty × skill coverage matrix.
2. Write a short content brief with learning goal, factual sources, key
   vocabulary, and intended misconception.
3. Draft the passage and items.
4. Run deterministic schema, duplication, source, answer-position, and
   coverage checks.
5. Complete a human editorial and educational review.
6. Sync canonical content to the frontend mirror.
7. Run backend tests, frontend tests, and the production Docker smoke harness.
8. Release as a small pull request.
9. Observe Reyana's engagement and question evidence before producing more of
   the same pattern.

AI may help draft or critique, but it is not the source of truth and should not
approve its own work.

### Human review rubric

Score each dimension 0–2:

- engagement and age appropriateness;
- passage clarity and coherence;
- skill/item alignment;
- evidence and answer correctness;
- distractor quality;
- factual and cultural care;
- difficulty fit and useful challenge.

Pass at 12/14 or higher, with no zero in correctness, safety, or factual and
cultural care.

## Automated quality gates

Add deterministic checks before scaling authorship:

- every reviewed activity has explicit difficulty;
- every question has a valid primary skill tag;
- every objective item has an explanation;
- every constructed response has guidance;
- every informational activity has approved sources;
- answer positions stay within a defined batch balance;
- repeated passage sentences and question prompts are reported;
- coverage matrix cannot regress;
- reviewed and draft content are explicitly distinguished;
- manifest and frontend mirror remain synchronized.

Keep the harness understandable. We do not currently need:

- multi-agent content orchestration;
- vector memory;
- an autonomous content factory;
- an LLM judge as the merge gate;
- automatic STAR score prediction.

The JSON library, deterministic audit report, Git history, human rubric, and
Reyana's observed question-level evidence are sufficient.

## Prioritized execution plan

### Batch 0 — Guardrails

- Add a content-audit command and regression tests.
- Stop assigning missing difficulty by activity ID for reviewed content.
- Add a reviewed/draft status or separate reviewed registry.
- Add answer-position, source, explanation, guidance, and duplication checks.
- Design separate reading and writing evidence for constructed responses.

### Batch 1 — Complete the weakest adaptive cells

Create nine reviewed activities emphasizing:

- difficult sequence/text structure;
- difficult key details;
- easy and medium main idea;
- medium key details;
- varied answer positions.

Use animals, human body, geography, school, and board-game themes so coverage
and interest improve together.

### Batch 2 — World and science awareness

Create nine reviewed activities across countries/maps, human body, animals,
and space. Balance literary framing with authoritative informational text.

### Batch 3 — High-engagement practice

Create nine reviewed activities across school mysteries, teacher situations,
friendship dilemmas, board-game strategy, and original music-performance
fantasy.

After Batch 3, the reviewed adaptive pool reaches the 36-activity target.

### Batches 4–6 — Legacy renovation

- Rewrite the 26 confirmed-boilerplate activities in small thematic groups.
- Migrate or retire the remaining 53 after individual editorial review.
- Do not let migration work crowd out observation of how the new reviewed core
  performs with Reyana.

## Success criteria

The expansion milestone is successful when:

- the reviewed adaptive pool has 36 activities and passes every quality gate;
- each core reading skill has at least four activities at each difficulty;
- no recommendation depends on synthetic ID-based difficulty;
- correct-answer position is not predictive;
- every reviewed informational passage has verified sources;
- every question produces interpretable evidence and useful feedback;
- Reyana completes sessions without recurring confusion or obvious boredom;
- parent-facing recommendations remain explainable from accumulated evidence.

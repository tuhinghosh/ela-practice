# Content Release D — Easy Mystery On-Ramp

## Purpose

Release D responds directly to learner feedback: Reyana wants more mysteries,
and the catalog needs more inviting passages that make it easy to begin a
session. These six activities use a mystery as the reading engine while still
building knowledge across science, animals, geography, history, the human
body, and space.

All six activities are `easy`. Easy means accessible language and clearly
signposted evidence, not shallow questions. Each passage establishes its
mystery in the opening paragraph, explains every essential unfamiliar idea in
context, and ends with a solution supported by clues.

This release intentionally tilts the full seed catalog toward easy content.
The catalog-level test therefore enforces a substantial floor for every tier
rather than exact numerical equality. The reviewed adaptive pool retains its
separate strict skill-by-difficulty coverage and regression gates.

## Production matrix

| ID | Working title | Knowledge domain | Mystery mechanism | Primary question skills | Likely misconception | Evidence demand |
| --- | --- | --- | --- | --- | --- | --- |
| `onramp-mystery-shadow-01` | The Message from the Dark Classroom | Light and shadows | A projected warning appears without a projector | sequence, vocabulary, inference, summary | A shadow is simply darkness with no relationship to a light source | Trace light, object, and screen clues in order |
| `onramp-mystery-class-pet-01` | The Case of the Sleepy Class Pet | Animal behavior | A normally active hamster hides during the day | reading comprehension, vocabulary, inference, summary | A daytime-resting animal must be sick | Combine nighttime evidence with the meaning of nocturnal |
| `onramp-mystery-map-island-01` | The Map with the Missing Island | Maps and geography | An island appears on one map but not another | main idea, vocabulary, reading comprehension, inference | Every accurate map must show every feature | Compare map purpose, scale, and symbols |
| `onramp-mystery-museum-clock-01` | The Museum Clock That Ran Backward | History and sundials | A shadow-clock seems to reverse direction | sequence, vocabulary, inference, summary | Historical tools work exactly like modern clocks | Reconstruct the demonstration and notice the reversed replica |
| `onramp-mystery-vanishing-voice-01` | The Mystery of the Vanishing Voice | Sound and hearing | A recorded whisper disappears in one location | reading comprehension, vocabulary, sequence, inference | Sound travels equally well through every setup | Connect vibration, distance, and a blocked microphone |
| `onramp-mystery-moon-footprints-01` | The Footprints Beside the Moon Base | Space science | Extra tracks appear outside a model Moon base | main idea, vocabulary, reading comprehension, summary | Footprints reveal weight but not movement or surface conditions | Use track shape, tread pattern, and low-gravity movement clues |

## Editorial constraints

- 325–425 words per passage, with short paragraphs and a concrete opening
  problem.
- Three multiple-choice questions and one constructed response.
- Correct answers deliberately rotate across positions.
- Essential terms are defined or demonstrated where first used.
- No crimes, threats, frightening danger, or adult-only stakes.
- No unexplained specialist knowledge is required to solve the mystery.
- The solution follows from visible textual evidence rather than a trick.
- No clue mechanism is repeated within the release.

## Promotion contract

Release D is promoted as one reviewed unit only after:

1. schema, manifest, synchronization, source, and duplication checks pass;
2. every activity scores at least 15/16 on the editorial preflight, with no
   zero and no undefined prerequisite concept;
3. the full backend, frontend, browser, build, and Docker checks pass;
4. the release is sampled in production through normal learner use, with
   reactions and completion evidence informing later allocation.

## Structured editorial preflight

Scores follow the eight 0–2 dimensions in the editorial harness: hook, clarity,
prerequisite support, skill alignment, answer quality, factual/safety care,
difficulty fit, and portfolio novelty.

| Activity | Scores | Total | Essential concept support | Opening goal and rewarding turn | Closest reviewed activity and difference |
| --- | --- | ---: | --- | --- | --- |
| The Message from the Dark Classroom | 2/2/2/2/2/2/2/2 | 16/16 | `shadow` is explained as blocked light; the arrow demonstrates `outline` and corrects the mirror misconception | Explain unexplained SOS letters; discover that the apparent warning is a planned Sunlight Observation Station | *The Upside-Down Message* explains vision informationally; this is a physical clue investigation about light paths |
| The Case of the Sleepy Class Pet | 2/2/2/2/2/2/2/1 | 15/16 | `nocturnal` is directly defined and supported by tape, footprints, and food evidence | Decide whether Nori's changed daytime behavior signals a problem; revise “I did not see it” into evidence of nighttime activity | *The Case of the Library Paw Prints* also uses animal traces, but here controlled before/after tests establish time-of-day behavior rather than identity |
| The Map with the Missing Island | 2/2/2/2/2/2/2/2 | 16/16 | `key` and `scale` are defined; classroom/school drawings model the area-detail tradeoff | Determine whether one of two current maps is wrong; discover that omission can be accurate when purpose and scale differ | *Zoom In Before Time Runs Out* changes maps to navigate a route; this compares apparent map disagreement through a familiar drawing experiment |
| The Museum Clock That Ran Backward | 2/2/2/2/2/2/2/2 | 16/16 | `sundial`, `gnomon`, and `replica` are defined before they carry question evidence | Diagnose a historical clock before opening; separate a working shadow mechanism from reversed labels | *The Stone With Three Voices* uses a museum artifact and historical evidence, but this reconstructs a mechanical labeling error through ordered observations |
| The Mystery of the Vanishing Voice | 2/2/2/2/2/2/2/2 | 16/16 | `vibrations`, absorption, echo, direct sound, and microphone are introduced through simple tests | Recover a whisper that disappears only in one booth; distinguish helpful wall absorption from harmful microphone blockage | *The Train That Rises Off the Track* introduces a physical mechanism, but this uses direct experiments with familiar sound and recording equipment |
| The Footprints Beside the Moon Base | 2/2/2/2/2/2/2/1 | 15/16 | `regolith` and `tread` are defined; the harness demonstration connects track shape to movement | Identify an apparent second visitor to a locked model base; discover that one boot can make two kinds of connected marks | *The Case of the Library Paw Prints* identifies an animal from prints; this infers movement from linked marks in a model low-gravity setting |

No activity has a zero, every total meets the 15/16 release threshold, and no
question requires an essential concept that the passage leaves undefined.
Human sampling remains the promotion boundary: review two of the six passages
(at least 30%), and reopen the closest pattern if either sample fails.

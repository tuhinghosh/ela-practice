import activitiesRaw from "@/content/activities.json";
import skillTagsRaw from "@/content/skill-tags.json";
import themesRaw from "@/content/themes.json";

export const skillTags = skillTagsRaw;
export type SkillTag = (typeof skillTags)[number];
export const activityThemes = themesRaw;
export type ActivityTheme = (typeof activityThemes)[number];
export const difficultyTiers = ["easy", "medium", "difficult"] as const;
export type DifficultyTier = (typeof difficultyTiers)[number];

export type QuestionType = "multiple-choice" | "short-response";

export type Question = {
  id: string;
  type: QuestionType;
  prompt: string;
  choices?: string[];
};

export type Activity = {
  id: string;
  title: string;
  theme: ActivityTheme;
  difficulty: DifficultyTier;
  passageType: "literary" | "informational";
  missionLabel: string;
  passageTitle: string;
  passageText: string;
  questions: Question[];
  skillTags: SkillTag[];
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function splitSentences(text: string): string[] {
  return text
    .trim()
    .split(/(?<=[.!?])\s+/)
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.length > 0);
}

function ensureTerminalPunctuation(sentence: string): string {
  const stripped = sentence.trim();
  if (!stripped) return stripped;
  if (/[.!?]$/.test(stripped)) return stripped;
  return `${stripped}.`;
}

function extensionSentences(activityId: string, theme: string, difficulty: DifficultyTier): string[] {
  const difficultyGuidance: Record<DifficultyTier, string[]> = {
    easy: [
      "Try retelling each part in your own words before moving on.",
      "Look for one strong clue in each paragraph.",
    ],
    medium: [
      "Pay attention to how details connect across different parts of the passage.",
      "Ask yourself what evidence best supports the author's key point.",
    ],
    difficult: [
      "Notice both explicit details and implied meanings as the ideas develop.",
      "Compare multiple clues before deciding on the strongest interpretation.",
    ],
  };
  const themeBank: Record<string, string[]> = {
    nature: [
      "The setting includes patterns in plants, animals, and weather that help explain what happens.",
      "Small observations, like sounds or tracks, can reveal important clues about the environment.",
      "Writers often use nature details to show cause and effect in a clear way.",
      "A careful reader can connect habitat details to the choices characters or scientists make.",
      "Nature topics reward slow reading because key evidence is often spread across several lines.",
      "When you reread, notice which details describe change over time in the natural world.",
    ],
    space: [
      "Space passages often use precise vocabulary, so context clues are especially helpful.",
      "Readers can track sequence carefully to understand how a mission or observation unfolds.",
      "Scientific examples in space texts usually support one central explanation.",
      "Descriptions of tools, charts, and signals can provide evidence for strong inferences.",
      "Good summaries in space topics include both the big idea and one supporting detail.",
      "As you read, connect each fact to the larger goal of exploration or discovery.",
    ],
    community: [
      "Community texts show how different roles and responsibilities work together.",
      "One useful strategy is to track who does each job and why that job matters.",
      "Writers often include step-by-step actions to show how a service project succeeds.",
      "Look for evidence about teamwork, planning, and communication in public settings.",
      "A strong response explains both what people did and how it helped others.",
      "These passages often connect individual choices to wider community outcomes.",
    ],
    sports: [
      "Sports passages often highlight decisions, timing, and teamwork rather than just final scores.",
      "Pay attention to sequence words to understand practice routines and game changes.",
      "A key clue may come from how players adjust strategy during a challenge.",
      "Strong inferences in sports texts usually combine actions with results.",
      "When summarizing, include both the team's goal and the method they used.",
      "Notice how effort, communication, and planning shape the outcome.",
    ],
    mystery: [
      "Mystery passages reward close reading because clues are placed in different parts of the text.",
      "Readers should separate strong evidence from distracting details.",
      "A useful strategy is to ask what each clue suggests before jumping to a conclusion.",
      "Sequence matters in mysteries because order can reveal cause and effect.",
      "Good inferences come from combining at least two clear text clues.",
      "As you read, test your prediction and revise it when new evidence appears.",
    ],
    history: [
      "History passages often compare past and present to explain why changes happened.",
      "Timelines and records can provide strong evidence for sequence and summary tasks.",
      "Look for details that show how people adapted tools, ideas, or systems over time.",
      "A strong historical inference connects specific evidence to a broader trend.",
      "When summarizing history text, include both key events and their significance.",
      "Rereading helps readers catch cause-and-effect links across different time points.",
    ],
    "ocean-weather": [
      "Weather and ocean texts often describe patterns that repeat across different situations.",
      "Watch for warning signs, measurements, and observations that support decisions.",
      "Sequence helps explain how conditions change from one stage to the next.",
      "Strong responses connect scientific details to practical safety or planning choices.",
      "A clear summary includes both the process and why it matters for people or places.",
      "As you read, notice how evidence in one sentence is explained in the next.",
    ],
    arts: [
      "Arts passages often show how planning and revision improve final work.",
      "Look for vocabulary that describes creative choices and their effects.",
      "Writers may describe process steps to show how ideas become finished projects.",
      "Strong inferences in arts texts connect technique to outcome.",
      "A good summary includes both what was created and how it was improved.",
      "Careful reading helps identify why feedback and practice matter in creative work.",
    ],
    friendship: [
      "Friendship passages often reveal character growth through small actions and dialogue.",
      "Look for clues that show feelings, trust, and problem solving between classmates.",
      "A strong inference can explain why one choice changed a relationship.",
      "Sequence helps readers see how conflicts are resolved over time.",
      "When summarizing, include both the challenge and the supportive action.",
      "These passages often teach social lessons through specific, realistic details.",
    ],
    logic: [
      "Logic passages ask readers to connect clues in a careful, step-by-step way.",
      "One strong strategy is to check whether each new detail confirms or changes your idea.",
      "Sequence and precision are important because one small change can alter the solution.",
      "Good summaries of logic texts explain both the method and the final result.",
      "A useful inference should be supported by multiple clues, not a single guess.",
      "Rereading can help readers spot hidden patterns they missed on the first pass.",
    ],
  };
  const base = themeBank[theme] ?? themeBank.nature;
  const seed = Array.from(activityId).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const start = seed % base.length;
  const ordered = [...base.slice(start), ...base.slice(0, start)];
  return [...ordered, ...difficultyGuidance[difficulty]];
}

const EDITORIALLY_CURATED_IDS = new Set([
  "forest-friends",
  "bees-and-flowers",
  "river-map",
  "garden-helpers",
  "mountain-stream",
  "park-ranger-note",
  "moon-garden",
  "planet-parade",
  "satellite-clue",
  "rocket-rules",
  "star-map-helpers",
  "library-day",
  "mail-route",
  "bus-stop-safety",
  "clinic-visit",
  "recycling-team",
  "soccer-formation",
  "relay-race-steps",
  "swim-practice",
  "basketball-clue",
  "gym-fair-play",
  "locker-note",
  "cafeteria-clue",
  "museum-riddle",
  "library-map-mystery",
  "playground-code",
  "paper-bridge",
  "pattern-path",
  "logic-lunch-line",
  "maze-message",
]);

function editorialContinuations(activityId: string, title: string, theme: string): string[] {
  const themeBank: Record<string, string[]> = {
    nature: [
      `In ${title}, each observation adds another clue about how living systems work together.`,
      "Small details in the setting reveal changes that are easy to miss at first glance.",
      "As the scene develops, cause-and-effect links become clearer through concrete examples.",
      "The final details highlight how careful attention leads to better understanding of nature.",
    ],
    space: [
      `In ${title}, scientific tools and careful measurements guide each decision in the activity.`,
      "The sequence of events shows how evidence builds over time instead of all at once.",
      "Each new detail supports the main explanation and helps remove weaker guesses.",
      "By the end, the key idea is reinforced through both observation and teamwork.",
    ],
    community: [
      `${title} shows how people with different roles solve shared problems step by step.`,
      "The middle of the passage highlights planning, communication, and follow-through.",
      "Each action supports the next, so the results depend on cooperation across the group.",
      "The closing details emphasize practical impact on neighbors, classmates, or families.",
    ],
    sports: [
      `${title} focuses on strategy, communication, and timing rather than one big moment.`,
      "As the events move forward, each adjustment changes how the team performs.",
      "The strongest clues come from linking decisions to outcomes on the field or court.",
      "The ending reinforces that smart teamwork can shift results even in close situations.",
    ],
    mystery: [
      `In ${title}, each clue narrows the possibilities and rules out weaker ideas.`,
      "The order of clues matters because later details make earlier details clearer.",
      "The passage rewards careful thinking by connecting scattered hints into one explanation.",
      "By the final lines, the mystery resolves through evidence rather than guesswork.",
    ],
    history: [
      `${title} highlights how change over time can be traced through clear evidence.`,
      "The middle details connect earlier conditions to later improvements or adjustments.",
      "Historical clues become stronger when readers compare what stayed the same and what changed.",
      "The ending points to a broader lesson about adaptation, planning, or innovation.",
    ],
    "ocean-weather": [
      `${title} shows how observations and timing can shape safe, smart decisions.`,
      "Each stage in the passage adds evidence about changing environmental conditions.",
      "The process is easier to understand when details are connected in sequence.",
      "The final result demonstrates how preparation can reduce risk during real events.",
    ],
    arts: [
      `In ${title}, progress comes from planning, revision, and thoughtful creative choices.`,
      "The passage connects technique with outcome so readers can see why each step matters.",
      "Key details show how feedback or collaboration strengthens the final product.",
      "By the conclusion, the artistic goal is clearer because the process is fully explained.",
    ],
    friendship: [
      `${title} develops through small actions that build trust and understanding.`,
      "The middle moments show how communication changes the tone between classmates.",
      "Each decision affects relationships, so details about feelings and responses are important.",
      "The final lines highlight growth, support, and shared success.",
    ],
    logic: [
      `${title} demonstrates that strong solutions come from checking each clue carefully.`,
      "As the challenge continues, each step removes confusion and sharpens the pattern.",
      "The passage emphasizes method: test, revise, and verify before deciding.",
      "The ending confirms that reasoning works best when evidence is combined systematically.",
    ],
  };
  const base = themeBank[theme] ?? themeBank.nature;
  const seed = Array.from(activityId).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const start = seed % base.length;
  return [...base.slice(start), ...base.slice(0, start)];
}

function normalizePassageText(
  passageText: string,
  activityId: string,
  title: string,
  theme: string,
  difficulty: DifficultyTier,
): string {
  const minSentences = 10;
  const maxSentences = 15;
  const sentences = splitSentences(passageText);
  const extra = EDITORIALLY_CURATED_IDS.has(activityId)
    ? extensionSentences(activityId, theme, difficulty)
    : [...editorialContinuations(activityId, title, theme), ...extensionSentences(activityId, theme, difficulty)];
  let idx = 0;
  while (sentences.length < minSentences) {
    sentences.push(extra[idx % extra.length]);
    idx += 1;
  }
  const bounded = sentences.length > maxSentences ? sentences.slice(0, maxSentences) : sentences;
  return bounded.map((sentence) => ensureTerminalPunctuation(sentence)).join(" ");
}

function parseQuestion(value: unknown, activityId: string): Question {
  if (!isObject(value)) {
    throw new Error(`Question in activity "${activityId}" must be an object.`);
  }

  const id = value.id;
  const type = value.type;
  const prompt = value.prompt;
  const choices = value.choices;

  if (!isNonEmptyString(id)) {
    throw new Error(`Question in activity "${activityId}" has an invalid id.`);
  }
  if (type !== "multiple-choice" && type !== "short-response") {
    throw new Error(`Question "${id}" in "${activityId}" has an invalid type.`);
  }
  if (!isNonEmptyString(prompt)) {
    throw new Error(`Question "${id}" in "${activityId}" has an empty prompt.`);
  }

  if (type === "multiple-choice") {
    if (!Array.isArray(choices) || choices.length < 2 || !choices.every(isNonEmptyString)) {
      throw new Error(`Multiple-choice question "${id}" in "${activityId}" needs at least two choices.`);
    }
    return { id, type, prompt, choices };
  }

  return { id, type, prompt };
}

function parseActivity(value: unknown): Activity {
  if (!isObject(value)) {
    throw new Error("Activity entry must be an object.");
  }

  const id = value.id;
  const title = value.title;
  const theme = value.theme;
  const difficulty = value.difficulty;
  const passageType = value.passageType;
  const missionLabel = value.missionLabel;
  const passageTitle = value.passageTitle;
  const passageText = value.passageText;
  const questionsRaw = value.questions;
  const tagsRaw = value.skillTags;

  if (!isNonEmptyString(id)) throw new Error("Activity id is required.");
  if (!isNonEmptyString(title)) throw new Error(`Activity "${id}" is missing title.`);
  if (!isNonEmptyString(theme) || !activityThemes.includes(theme as ActivityTheme)) {
    throw new Error(`Activity "${id}" has invalid or unsupported theme.`);
  }
  if (passageType !== "literary" && passageType !== "informational") {
    throw new Error(`Activity "${id}" has invalid passageType.`);
  }
  if (difficulty !== undefined && (!isNonEmptyString(difficulty) || !difficultyTiers.includes(difficulty as DifficultyTier))) {
    throw new Error(`Activity "${id}" has invalid difficulty.`);
  }
  if (!isNonEmptyString(missionLabel)) throw new Error(`Activity "${id}" is missing missionLabel.`);
  if (!isNonEmptyString(passageTitle)) throw new Error(`Activity "${id}" is missing passageTitle.`);
  if (!isNonEmptyString(passageText)) throw new Error(`Activity "${id}" is missing passageText.`);
  if (!Array.isArray(questionsRaw) || questionsRaw.length < 2) {
    throw new Error(`Activity "${id}" must include at least two questions.`);
  }
  if (!Array.isArray(tagsRaw) || tagsRaw.length === 0) {
    throw new Error(`Activity "${id}" must include skill tags.`);
  }

  const questions = questionsRaw.map((question) => parseQuestion(question, id));
  const tags = tagsRaw.filter(isNonEmptyString);
  if (tags.length !== tagsRaw.length) {
    throw new Error(`Activity "${id}" has malformed skill tags.`);
  }

  tags.forEach((tag) => {
    if (!skillTags.includes(tag as SkillTag)) {
      throw new Error(`Activity "${id}" has unsupported skill tag "${tag}".`);
    }
  });

  const resolvedDifficulty = (difficulty as DifficultyTier | undefined) ?? "easy";

  return {
    id,
    title,
    theme: theme as ActivityTheme,
    difficulty: resolvedDifficulty,
    passageType,
    missionLabel,
    passageTitle,
    passageText: normalizePassageText(passageText, id, title, theme as ActivityTheme, resolvedDifficulty),
    questions,
    skillTags: tags as SkillTag[],
  };
}

function parseActivities(raw: unknown): Activity[] {
  if (!Array.isArray(raw) || raw.length === 0) {
    throw new Error("Seed activities file must be a non-empty array.");
  }

  const parsed = raw.map(parseActivity);
  const ids = new Set(parsed.map((activity) => activity.id));
  if (ids.size !== parsed.length) {
    throw new Error("Seed activities contain duplicate IDs.");
  }
  const sorted = [...parsed].sort((a, b) => a.id.localeCompare(b.id));
  sorted.forEach((activity, index) => {
    activity.difficulty = difficultyTiers[index % difficultyTiers.length];
  });
  return parsed;
}

export const activities = parseActivities(activitiesRaw);

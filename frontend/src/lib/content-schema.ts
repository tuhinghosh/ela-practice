import activitiesRaw from "@/content/activities.json";
import skillTagsRaw from "@/content/skill-tags.json";
import themesRaw from "@/content/themes.json";

export const skillTags = skillTagsRaw;
export type SkillTag = (typeof skillTags)[number];
export const activityThemes = themesRaw;
export type ActivityTheme = (typeof activityThemes)[number];
export const difficultyTiers = ["easy", "medium", "difficult"] as const;
export type DifficultyTier = (typeof difficultyTiers)[number];
const MIN_PASSAGE_SENTENCES = 8;
const MIN_PASSAGE_PARAGRAPHS = 2;
const MIN_PARAGRAPH_SENTENCES = 2;
const SETUP_CUES = [
  "needed to",
  "had to",
  "problem",
  "challenge",
  "question",
  "goal",
  "plan",
  "clue",
  "worried",
  "noticed",
  "task",
  "decided",
  "wanted",
  "tried",
  "began",
  "hoped",
  "set out",
  "wondered",
] as const;
const OUTCOME_CUES = [
  "by the end",
  "learned",
  "as a result",
  "this showed",
  "this helped",
  "improved",
  "solved",
  "understood",
  "agreed",
  "realized",
  "discovered",
  "finally",
  "after that",
  "from then on",
  "knew",
] as const;

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
  passageType: "literary" | "informational" | "poetry";
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

function sentenceCount(text: string): number {
  return text
    .replace(/\n/g, " ")
    .trim()
    .split(/(?<=[.!?])\s+/)
    .filter((chunk) => chunk.trim().length > 0).length;
}

function paragraphCount(text: string): number {
  return text
    .trim()
    .split(/\n\s*\n/)
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.length > 0).length;
}

function splitParagraphs(text: string): string[] {
  return text
    .trim()
    .split(/\n\s*\n/)
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.length > 0);
}

function hasAnyCue(text: string, cues: readonly string[]): boolean {
  const lowered = text.toLowerCase();
  return cues.some((cue) => lowered.includes(cue));
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
  if (passageType !== "literary" && passageType !== "informational" && passageType !== "poetry") {
    throw new Error(`Activity "${id}" has invalid passageType.`);
  }
  if (difficulty !== undefined && (!isNonEmptyString(difficulty) || !difficultyTiers.includes(difficulty as DifficultyTier))) {
    throw new Error(`Activity "${id}" has invalid difficulty.`);
  }
  if (!isNonEmptyString(missionLabel)) throw new Error(`Activity "${id}" is missing missionLabel.`);
  if (!isNonEmptyString(passageTitle)) throw new Error(`Activity "${id}" is missing passageTitle.`);
  if (!isNonEmptyString(passageText)) throw new Error(`Activity "${id}" is missing passageText.`);
  if (passageType === "poetry") {
    const lines = passageText.split("\n").filter((line) => line.trim().length > 0);
    const stanzas = passageText.split("\n\n").filter((s) => s.trim().length > 0);
    if (lines.length < 8) {
      throw new Error(`Poetry activity "${id}" must include at least 8 lines.`);
    }
    if (stanzas.length < 2) {
      throw new Error(`Poetry activity "${id}" must include at least 2 stanzas.`);
    }
  } else {
    if (sentenceCount(passageText) < MIN_PASSAGE_SENTENCES) {
      throw new Error(`Activity "${id}" must include at least ${MIN_PASSAGE_SENTENCES} sentences in passageText.`);
    }
    if (paragraphCount(passageText) < MIN_PASSAGE_PARAGRAPHS) {
      throw new Error(`Activity "${id}" must include at least ${MIN_PASSAGE_PARAGRAPHS} paragraphs in passageText.`);
    }
    const paragraphs = splitParagraphs(passageText);
    if (sentenceCount(paragraphs[0] ?? "") < MIN_PARAGRAPH_SENTENCES) {
      throw new Error(`Activity "${id}" first paragraph must include at least ${MIN_PARAGRAPH_SENTENCES} sentences.`);
    }
    if (sentenceCount(paragraphs[1] ?? "") < MIN_PARAGRAPH_SENTENCES) {
      throw new Error(`Activity "${id}" second paragraph must include at least ${MIN_PARAGRAPH_SENTENCES} sentences.`);
    }
    if (!hasAnyCue(paragraphs[0] ?? "", SETUP_CUES)) {
      throw new Error(`Activity "${id}" first paragraph must include setup/challenge context cues.`);
    }
    if (!hasAnyCue(passageText, OUTCOME_CUES)) {
      throw new Error(`Activity "${id}" must include outcome/reflection cues in the passage.`);
    }
  }
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
    passageText,
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

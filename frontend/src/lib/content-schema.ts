import activitiesRaw from "@/content/activities.json";
import skillTagsRaw from "@/content/skill-tags.json";
import themesRaw from "@/content/themes.json";

export const skillTags = skillTagsRaw;
export type SkillTag = (typeof skillTags)[number];
export const activityThemes = themesRaw;
export type ActivityTheme = (typeof activityThemes)[number];

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

  return {
    id,
    title,
    theme: theme as ActivityTheme,
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
  return parsed;
}

export const activities = parseActivities(activitiesRaw);

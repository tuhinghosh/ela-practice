import { activities, skillTags } from "@/lib/content-schema";

export type { Activity, Question, QuestionType, SkillTag } from "@/lib/content-schema";

export type RewardSnapshot = {
  stars: number;
  streakDays: number;
  badges: string[];
};

export const rewardSnapshot: RewardSnapshot = {
  stars: 14,
  streakDays: 3,
  badges: ["Story Explorer", "Vocabulary Finder"],
};

export const recentSessions = [
  { id: "session-001", activityTitle: "Forest Friends", scoreLabel: "4/5", skill: "inference" },
  { id: "session-002", activityTitle: "How Bees Help Flowers", scoreLabel: "5/5", skill: "main-idea" },
  { id: "session-003", activityTitle: "The Lost Map", scoreLabel: "3/5", skill: "summary" },
];

export { activities, skillTags };

export const parentProgressHighlights = {
  totalActivities: 8,
  strongestSkill: "Main idea and details",
  growthArea: "Sentence completeness in written responses",
};

export const coachSample = {
  celebration: "You worked hard and used evidence from the story. Nice effort!",
  explanation:
    "Your best answer points to the bird flying back for the twig. That clue supports the idea of not giving up.",
  nextStepSuggestion: "Try another activity focused on inference and explain your evidence in 2-3 sentences.",
};

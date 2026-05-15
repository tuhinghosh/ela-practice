import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";

import ParentProgressPage from "./page";

const baseProgress: api.ParentProgressResponse = {
  child_profile: { display_name: "Test Kid", grade_level: 3 },
  summary: {
    session_count: 5,
    average_score_percent: 78,
    last_submitted_at: "2026-05-14T10:00:00Z",
    strengths: ["inference"],
    growth_areas: ["summary"],
    trend: "improving",
    skill_summary: { strength: "inference", struggle: "summary" },
  },
  recent_sessions: [],
  writing_feedback_summaries: [],
  skill_history: {
    "7_day": {},
    "30_day": {
      summary: { attempts: 4, avg_score: 55 },
      "sentence-quality": { attempts: 3, avg_score: 70 },
    },
    all_time: {},
  },
  practice_next: [
    { skill: "summary", avg_score: 55, attempts: 4 },
    { skill: "sentence-quality", avg_score: 70, attempts: 3 },
  ],
  rewards: {
    stars: 12,
    streak_days: 4,
    badges: ["Three Mission Starter", "Story Explorer"],
  },
  ai_usage: {
    enabled: true,
    used: 7,
    limit: 50,
    remaining: 43,
    reset_at: "2026-05-16T00:00:00+00:00",
  },
  recent_questions: [
    {
      session_id: "s-1",
      activity_id: "nature-01",
      activity_title: "Lila and the Oak",
      question_id: "q1",
      question_type: "multiple-choice",
      prompt: "What happened to Lila's plant?",
      skill_tags: ["reading-comprehension"],
      submitted_at: "2026-05-14T10:00:00Z",
      child_answer: "Roots took the water",
      correct_answer: "Roots took the water",
      is_correct: true,
    },
    {
      session_id: "s-1",
      activity_id: "nature-01",
      activity_title: "Lila and the Oak",
      question_id: "q2",
      question_type: "multiple-choice",
      prompt: "Which word fits?",
      skill_tags: ["vocabulary"],
      submitted_at: "2026-05-14T10:01:00Z",
      child_answer: "wrong choice",
      correct_answer: "correct choice",
      is_correct: false,
    },
    {
      session_id: "s-1",
      activity_id: "nature-01",
      activity_title: "Lila and the Oak",
      question_id: "q4",
      question_type: "short-response",
      prompt: "Explain why Lila kept trying.",
      skill_tags: ["short-writing"],
      submitted_at: "2026-05-14T10:02:00Z",
      child_answer: null,
      correct_answer: null,
      is_correct: null,
    },
  ],
};

describe("ParentProgressPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "getParentProgress").mockResolvedValue(baseProgress);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function cardForHeading(name: string): HTMLElement {
    const heading = screen.getByRole("heading", { name });
    const card = heading.closest("article");
    if (!card) throw new Error(`No <article> ancestor for heading ${name}`);
    return card as HTMLElement;
  }

  it("renders practice-next suggestions and 30-day skill breakdown", async () => {
    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Practice next" })).toBeInTheDocument();
    });

    const practiceCard = cardForHeading("Practice next");
    expect(practiceCard).toHaveTextContent("summary");
    expect(practiceCard).toHaveTextContent("55% over 4 attempts");
    expect(practiceCard).toHaveTextContent("sentence-quality");

    const breakdownCard = cardForHeading("Last 30 days by skill");
    expect(breakdownCard).toHaveTextContent("summary");
    expect(breakdownCard).toHaveTextContent("55% (4)");
    expect(breakdownCard).toHaveTextContent("sentence-quality");
    expect(breakdownCard).toHaveTextContent("70% (3)");
  });

  it("shows a friendly empty state when no suggestions are available", async () => {
    vi.spyOn(api, "getParentProgress").mockResolvedValue({
      ...baseProgress,
      practice_next: [],
      skill_history: { "7_day": {}, "30_day": {}, all_time: {} },
      recent_questions: [],
    });

    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Practice next" })).toBeInTheDocument();
    });

    const practiceCard = cardForHeading("Practice next");
    expect(practiceCard).toHaveTextContent(/once your child completes a few more activities/i);

    const breakdownCard = cardForHeading("Last 30 days by skill");
    expect(breakdownCard).toHaveTextContent("No skill data in the last 30 days yet.");

    const recentCard = cardForHeading("Recent questions");
    expect(recentCard).toHaveTextContent("No recent questions yet.");
  });

  it("renders the reward summary card with streak, stars, and badge count", async () => {
    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Reward summary" })).toBeInTheDocument();
    });

    const card = cardForHeading("Reward summary");
    expect(card).toHaveTextContent("Streak (days)");
    expect(card).toHaveTextContent("4");
    expect(card).toHaveTextContent("Stars");
    expect(card).toHaveTextContent("12");
    expect(card).toHaveTextContent("Badges");
    // Badge count, not the names — the names live on the child reward
    // celebration, not the parent summary.
    expect(card).toHaveTextContent("2");
  });

  it("renders the AI usage card with used/limit and remaining + reset_at", async () => {
    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "AI usage today" })).toBeInTheDocument();
    });
    const card = cardForHeading("AI usage today");
    expect(card).toHaveTextContent("7 / 50");
    expect(card).toHaveTextContent(/43 remaining/);
    expect(card).toHaveTextContent(/Resets at/);
  });

  it("shows the unlimited copy when the daily cap is disabled", async () => {
    vi.spyOn(api, "getParentProgress").mockResolvedValue({
      ...baseProgress,
      ai_usage: {
        enabled: false,
        used: 99,
        limit: 0,
        remaining: null,
        reset_at: "2026-05-16T00:00:00+00:00",
      },
    });

    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "AI usage today" })).toBeInTheDocument();
    });
    const card = cardForHeading("AI usage today");
    expect(card).toHaveTextContent("99");
    expect(card).toHaveTextContent(/No daily cap configured/i);
    expect(card).not.toHaveTextContent("/ 0");
  });

  it("renders recent questions with correctness badges and skill chips", async () => {
    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Recent questions" })).toBeInTheDocument();
    });

    const card = cardForHeading("Recent questions");
    expect(card).toHaveTextContent("Lila and the Oak · Correct");
    expect(card).toHaveTextContent("Lila and the Oak · Needs review");
    expect(card).toHaveTextContent("Lila and the Oak · Written response");
    expect(card).toHaveTextContent("Skills: short-writing");
    // Question prompts (not child answers) are shown so parents know what was asked.
    expect(card).toHaveTextContent("What happened to Lila's plant?");
    expect(card).toHaveTextContent("Explain why Lila kept trying.");
  });
});

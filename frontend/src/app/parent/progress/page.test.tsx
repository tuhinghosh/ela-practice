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
    });

    render(<ParentProgressPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Practice next" })).toBeInTheDocument();
    });

    const practiceCard = cardForHeading("Practice next");
    expect(practiceCard).toHaveTextContent(/once your child completes a few more activities/i);

    const breakdownCard = cardForHeading("Last 30 days by skill");
    expect(breakdownCard).toHaveTextContent("No skill data in the last 30 days yet.");
  });
});

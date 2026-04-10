import { describe, expect, it } from "vitest";

import { activities, coachSample, rewardSnapshot } from "./mock-data";

describe("mock data", () => {
  it("has at least one seeded activity with both question types", () => {
    expect(activities.length).toBeGreaterThanOrEqual(50);

    const activity = activities[0];
    const types = new Set(activity.questions.map((question) => question.type));
    expect(types.has("multiple-choice")).toBe(true);
    expect(types.has("short-response")).toBe(true);
  });

  it("covers multiple themes for browsing", () => {
    const themes = new Set(activities.map((activity) => activity.theme));
    expect(themes.size).toBeGreaterThanOrEqual(8);
  });

  it("has balanced activity difficulty tiers", () => {
    const counts = activities.reduce(
      (acc, activity) => {
        acc[activity.difficulty] += 1;
        return acc;
      },
      { easy: 0, medium: 0, difficult: 0 },
    );

    expect(counts.easy).toBeGreaterThan(0);
    expect(counts.medium).toBeGreaterThan(0);
    expect(counts.difficult).toBeGreaterThan(0);
    expect(Math.max(counts.easy, counts.medium, counts.difficult) - Math.min(counts.easy, counts.medium, counts.difficult)).toBeLessThanOrEqual(1);
  });

  it("contains reward and coach placeholders for shell screens", () => {
    expect(rewardSnapshot.stars).toBeGreaterThanOrEqual(0);
    expect(coachSample.celebration.length).toBeGreaterThan(0);
    expect(coachSample.explanation.length).toBeGreaterThan(0);
  });
});

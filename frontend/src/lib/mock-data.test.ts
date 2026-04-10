import { describe, expect, it } from "vitest";

import { activities, coachSample, rewardSnapshot } from "./mock-data";

describe("mock data", () => {
  it("has at least one seeded activity with both question types", () => {
    expect(activities.length).toBeGreaterThan(0);

    const activity = activities[0];
    const types = new Set(activity.questions.map((question) => question.type));
    expect(types.has("multiple-choice")).toBe(true);
    expect(types.has("short-response")).toBe(true);
  });

  it("contains reward and coach placeholders for shell screens", () => {
    expect(rewardSnapshot.stars).toBeGreaterThanOrEqual(0);
    expect(coachSample.celebration.length).toBeGreaterThan(0);
    expect(coachSample.explanation.length).toBeGreaterThan(0);
  });
});

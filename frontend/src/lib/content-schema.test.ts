import { describe, expect, it } from "vitest";

import { activities, skillTags } from "./content-schema";

describe("content schema", () => {
  it("loads non-empty seeded activities", () => {
    expect(activities.length).toBeGreaterThan(0);
  });

  it("covers literary and informational passages", () => {
    const passageTypes = new Set(activities.map((activity) => activity.passageType));
    expect(passageTypes.has("literary")).toBe(true);
    expect(passageTypes.has("informational")).toBe(true);
  });

  it("ensures activities use valid skill tags", () => {
    activities.forEach((activity) => {
      activity.skillTags.forEach((tag) => {
        expect(skillTags.includes(tag)).toBe(true);
      });
    });
  });
});

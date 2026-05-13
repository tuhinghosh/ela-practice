import { expect, test } from "@playwright/test";

import activities from "../../src/content/activities.json";

test("all seeded activities render passage and question types", async ({ page }) => {
  expect(activities.length).toBeGreaterThanOrEqual(50);

  for (const activity of activities.slice(0, 10)) {
    await page.goto(`/activity/${activity.id}`);
    await expect(page.getByRole("heading", { name: activity.title, level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: activity.passageTitle, level: 2 })).toBeVisible();

    const multipleChoiceQuestion = activity.questions.find((question) => question.type === "multiple-choice");
    if (multipleChoiceQuestion) {
      await expect(page.getByText(multipleChoiceQuestion.prompt)).toBeVisible();
    }

    const shortResponseQuestion = activity.questions.find((question) => question.type === "short-response");
    if (shortResponseQuestion) {
      await expect(page.getByText(shortResponseQuestion.prompt)).toBeVisible();
      await expect(page.getByLabel("Short response input")).toBeVisible();
    }
  }
});

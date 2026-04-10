import { expect, test } from "@playwright/test";

import activities from "../../src/content/activities.json";

test("all seeded activities render passage and question types", async ({ page }) => {
  for (const activity of activities) {
    await page.goto(`/activity/${activity.id}`);
    await expect(page.getByRole("heading", { name: activity.title })).toBeVisible();
    await expect(page.getByRole("heading", { name: activity.passageTitle })).toBeVisible();

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

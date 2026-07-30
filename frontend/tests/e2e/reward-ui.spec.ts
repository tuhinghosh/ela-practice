import { expect, test } from "@playwright/test";
const ACTIVITY_ID = "nature-01";
const ACTIVITY_TITLE = "The Seed That Wouldn't Grow";
const SESSION_ID = "session-live-001";

test("results screen shows updated reward celebration after submit", async ({ page }) => {
  await page.route(`**/api/activities/${ACTIVITY_ID}/start`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: SESSION_ID,
        activity_id: ACTIVITY_ID,
        started_at: "2026-04-09T00:00:00Z",
        resumed: false,
      }),
    });
  });
  await page.route(`**/api/activities/${ACTIVITY_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: ACTIVITY_ID,
        title: ACTIVITY_TITLE,
        passage_type: "literary",
        mission_label: "Today's quest",
        passage_title: "A Visit to Pine Hill",
        passage_text: "Story text",
        skill_tags: ["reading-comprehension", "short-writing"],
        questions: [
          {
            id: "q1",
            type: "multiple-choice",
            prompt: "What is the main idea of this story?",
            choices: [
              "Mira forgot her lunch on Pine Hill.",
              "The birds show teamwork while building a nest.",
            ],
          },
          {
            id: "q2",
            type: "short-response",
            prompt: "Write 2-3 sentences explaining one clue that shows the birds did not give up.",
          },
        ],
      }),
    });
  });

  await page.route(`**/api/activities/${ACTIVITY_ID}/submit`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: SESSION_ID,
        activity_id: ACTIVITY_ID,
        total_score: 1.8,
        max_score: 2,
        score_percent: 90,
        rubric: {
          completion: "meets",
          relevance: "meets",
          sentence_completeness: "meets",
          skill_specific_checks: ["evidence reference"],
        },
        skill_breakdown: { "main-idea": 100, inference: 80 },
        question_results: [
          {
            question_id: "q1",
            question_type: "multiple-choice",
            prompt: "What is the main idea of this story?",
            skill_tag: "main-idea",
            child_answer: "The birds show teamwork while building a nest.",
            correct_answer: "The birds show teamwork while building a nest.",
            is_correct: true,
            explanation: "The birds repeatedly work together to finish the nest.",
          },
          {
            question_id: "q2",
            question_type: "short-response",
            prompt: "Write 2-3 sentences explaining one clue that shows the birds did not give up.",
            skill_tag: "inference",
            child_answer: "The bird came back because it did not give up.",
            correct_answer: null,
            is_correct: null,
            explanation: "Your response was complete and connected to the passage.",
          },
        ],
        reward_snapshot: {
          stars_before: 6,
          stars_after: 8,
          stars_earned: 2,
          streak_before: 3,
          streak_after: 4,
          badges_before: ["Story Explorer"],
          badges_after: ["Story Explorer", "Three Mission Starter"],
          new_badges: ["Three Mission Starter"],
          points_earned: 20,
          total_points: 80,
        },
      }),
    });
  });

  await page.route(`**/api/sessions/${SESSION_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: SESSION_ID,
        activity_id: ACTIVITY_ID,
        activity_title: ACTIVITY_TITLE,
        submitted_at: "2026-04-09T00:00:00Z",
        total_score: 1.8,
        max_score: 2,
        score_percent: 90,
        rubric: {
          completion: "meets",
          relevance: "meets",
          sentence_completeness: "meets",
          skill_specific_checks: ["evidence reference"],
        },
        skill_breakdown: { "main-idea": 100, inference: 80 },
        question_results: [
          {
            question_id: "q1",
            question_type: "multiple-choice",
            prompt: "What is the main idea of this story?",
            skill_tag: "main-idea",
            child_answer: "The birds show teamwork while building a nest.",
            correct_answer: "The birds show teamwork while building a nest.",
            is_correct: true,
            explanation: "The birds repeatedly work together to finish the nest.",
          },
          {
            question_id: "q2",
            question_type: "short-response",
            prompt: "Write 2-3 sentences explaining one clue that shows the birds did not give up.",
            skill_tag: "inference",
            child_answer: "The bird came back because it did not give up.",
            correct_answer: null,
            is_correct: null,
            explanation: "Your response was complete and connected to the passage.",
          },
        ],
        reward_snapshot: {
          stars_before: 6,
          stars_after: 8,
          stars_earned: 2,
          streak_before: 3,
          streak_after: 4,
          badges_before: ["Story Explorer"],
          badges_after: ["Story Explorer", "Three Mission Starter"],
          new_badges: ["Three Mission Starter"],
          points_earned: 20,
          total_points: 80,
        },
      }),
    });
  });
  await page.route(`**/api/sessions/${SESSION_ID}/reaction`, async (route) => {
    const payload = route.request().postDataJSON() as { reaction: string };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ session_id: SESSION_ID, reaction: payload.reaction }),
    });
  });

  await page.goto(`/activity/${ACTIVITY_ID}`);
  await page.getByLabel("The birds show teamwork while building a nest.").click();
  await page.getByLabel("Short response input").fill("The bird came back because it did not give up.");
  await page.getByRole("button", { name: "Submit answers" }).click();

  await expect(page.getByRole("heading", { name: /Results:/ })).toBeVisible();
  await expect(page.getByText("You earned +2 stars")).toBeVisible();
  await expect(page.getByText("Total points: 80")).toBeVisible();
  await expect(page.getByText("New badge unlocked: Three Mission Starter.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Skills from this mission" })).toBeVisible();
  await expect(page.getByText("Main Idea", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review your answers" })).toBeVisible();
  await expect(page.getByText("The birds repeatedly work together to finish the nest.")).toBeVisible();
  await page.getByRole("button", { name: "Fun", exact: true }).click();
  await expect(page.getByText("Saved: fun.")).toBeVisible();
});

import { expect, test, type Page } from "@playwright/test";

async function mockActivityAndSubmission(page: Page) {
  await page.route("**/api/activities/forest-friends", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "forest-friends",
        title: "Forest Friends",
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

  await page.route("**/api/activities/forest-friends/submit", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "session-live-001",
        activity_id: "forest-friends",
        total_score: 1.8,
        max_score: 2,
        score_percent: 90,
        rubric: {
          completion: "meets",
          relevance: "meets",
          sentence_completeness: "meets",
          skill_specific_checks: ["evidence reference"],
        },
        skill_breakdown: { inference: 90 },
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

  await page.route("**/api/sessions/session-live-001", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "session-live-001",
        activity_id: "forest-friends",
        activity_title: "Forest Friends",
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
        skill_breakdown: { inference: 90 },
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
}

test("ai coach panel supports asking limited post-submission questions", async ({ page }) => {
  await mockActivityAndSubmission(page);

  let coachCalls = 0;
  await page.route("**/api/ai/coach", async (route) => {
    coachCalls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        message_to_child: "Great effort today!",
        message_to_parent: "Strong persistence this session.",
        hint: "Point to one clue from the passage.",
        explanation: "Your answer improves when you cite evidence.",
        celebration: "Quest complete!",
        suggested_next_activity_id: "river-map",
        suggested_skill_tag: "inference",
        writing_feedback: "Add one more complete sentence.",
        confidence: 0.82,
        used_fallback: false,
        model: "openai/gpt-oss-120b",
      }),
    });
  });

  await page.goto("/activity/forest-friends");
  await page.getByLabel("The birds show teamwork while building a nest.").click();
  await page.getByLabel("Short response input").fill("The bird came back because it did not give up.");
  await page.getByRole("button", { name: "Submit answers" }).click();

  await expect(page.getByRole("heading", { name: "Reading Coach" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Try the next challenge" })).toBeVisible();

  await page.getByLabel("Ask the coach a question about this activity").fill("How can I improve my evidence sentence?");
  await page.getByRole("button", { name: "Ask coach" }).click();
  await expect.poll(() => coachCalls).toBeGreaterThan(1);
});

test("ai coach panel handles backend errors safely", async ({ page }) => {
  await mockActivityAndSubmission(page);

  await page.route("**/api/ai/coach", async (route) => {
    await route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "OpenRouter provider error while generating coach feedback." }),
    });
  });

  await page.goto("/activity/forest-friends");
  await page.getByLabel("The birds show teamwork while building a nest.").click();
  await page.getByLabel("Short response input").fill("The bird came back because it did not give up.");
  await page.getByRole("button", { name: "Submit answers" }).click();

  await expect(
    page.getByText("Coach is temporarily unavailable. You can continue your quest and try again soon."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: /Results:/ })).toBeVisible();
});

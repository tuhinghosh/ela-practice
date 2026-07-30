import { expect, test } from "@playwright/test";

test("parent progress shows trend skill summary and writing highlights", async ({ page }) => {
  await page.route("**/api/progress/parent", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        child_profile: { display_name: "Explorer Kid", grade_level: 3 },
        summary: {
          session_count: 4,
          average_score_percent: 82,
          last_submitted_at: "2026-04-09T00:00:00Z",
          strengths: ["inference"],
          growth_areas: ["sentence-quality"],
          trend: "improving",
          skill_summary: {
            strength: "inference",
            struggle: "sentence-quality",
          },
        },
        recent_sessions: [
          {
            session_id: "s1",
            activity_id: "forest-friends",
            activity_title: "Forest Friends",
            score_percent: 88,
            submitted_at: "2026-04-09T00:00:00Z",
          },
        ],
        writing_feedback_summaries: [
          {
            activity_title: "Forest Friends",
            summary: "Completion: meets; Relevance: meets; Sentence completeness: needs_work; Skill checks: evidence reference.",
          },
        ],
        adaptive_recommendation: {
          phase: "adaptive",
          activity_id: "pilot-mystery-cat-01",
          activity_title: "The Case of the Library Paw Prints",
          difficulty: "easy",
          target_skill: "inference",
          decision: "step-down",
          attempts: 4,
          avg_score: 55,
          reason: "Recent accuracy is 55%, below the 60% support threshold.",
          rule: "<3 observations: gather evidence; <60%: easier; 60–85%: hold; >85%: harder.",
        },
        engagement: {
          completed_with_timing: 4,
          median_elapsed_seconds: 420,
          open_attempts: 1,
          abandoned_attempts: 0,
          reactions: { fun: 3, okay: 1, confusing: 0 },
          confusing_activity_ids: [],
        },
      }),
    });
  });

  await page.goto("/parent/progress");
  await expect(page.getByRole("heading", { name: "Parent progress snapshot" })).toBeVisible();
  await expect(page.getByText("Trend", { exact: true })).toBeVisible();
  await expect(page.getByText("improving")).toBeVisible();
  await expect(page.getByText(/Writing feedback highlights/)).toBeVisible();
  await expect(page.getByText(/Sentence completeness: needs_work/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "How the next mission was chosen" })).toBeVisible();
  await expect(page.getByText("step-down", { exact: true })).toBeVisible();
  await expect(page.getByText(/below the 60% support threshold/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Engagement signals" })).toBeVisible();
  await expect(page.getByText("7 min")).toBeVisible();
});

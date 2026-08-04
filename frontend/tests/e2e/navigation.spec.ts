import { expect, test } from "@playwright/test";
test("main navigation reaches core Part 3 screens", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Welcome back, Reader!" })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Reyana's Missions" })).toBeVisible();
  await expect(page.getByText("Try these in any order—or choose any reviewed activity below.")).toBeVisible();
  await page.getByRole("button", { name: "Show me another" }).click();
  await expect(page.getByRole("heading", { name: "River Rescue" })).toBeVisible();
  await page.getByRole("link", { name: "Start this mission" }).click();
  await expect(page.getByRole("heading", { name: "River Rescue" })).toBeVisible();

  await page.getByRole("link", { name: "Missions" }).click();

  await page.getByRole("link", { name: "Parent View" }).click();
  await expect(page.getByRole("heading", { name: "Parent progress snapshot" })).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to start today's quest" })).toBeVisible();
});

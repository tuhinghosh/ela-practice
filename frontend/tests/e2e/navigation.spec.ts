import { expect, test } from "@playwright/test";

test("main navigation reaches core Part 3 screens", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Welcome back, Reader!" })).toBeVisible();

  await page.getByRole("link", { name: "Activity" }).click();
  await expect(page.getByRole("heading", { name: "Forest Friends" })).toBeVisible();

  await page.getByRole("link", { name: "Results" }).click();
  await expect(page.getByRole("heading", { name: /Results: Forest Friends/ })).toBeVisible();

  await page.getByRole("link", { name: "Parent View" }).click();
  await expect(page.getByRole("heading", { name: "Parent progress snapshot" })).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to start today's quest" })).toBeVisible();
});

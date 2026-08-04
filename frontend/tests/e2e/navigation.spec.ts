import { expect, test } from "@playwright/test";
test("main navigation reaches core Part 3 screens", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Welcome back, Reader!" })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Reyana's Missions" })).not.toBeVisible();
  const missionHeading = page.locator("h2").first();
  const initialTitle = (await missionHeading.textContent()) ?? "";
  await page.getByRole("button", { name: "Show me another" }).click();
  await expect(missionHeading).not.toHaveText(initialTitle);
  const secondTitle = (await missionHeading.textContent()) ?? "";
  await page.getByRole("button", { name: "Show me another" }).click();
  await expect(missionHeading).not.toHaveText(secondTitle);
  const chosenTitle = (await missionHeading.textContent()) ?? "";
  await page.getByRole("link", { name: "Start this mission" }).click();
  await expect(page.getByRole("heading", { name: chosenTitle })).toBeVisible();

  await page.getByRole("link", { name: "Missions" }).click();

  await page.getByRole("link", { name: "Parent View" }).click();
  await expect(page.getByRole("heading", { name: "Parent progress snapshot" })).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to start today's quest" })).toBeVisible();
});

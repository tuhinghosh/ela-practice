import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  // Keep tests in one spec serial. Several specs intentionally reuse the same
  // dynamic route, and compiling that route concurrently in `next dev` can
  // expose a partially written development payload on slower CI runners.
  // Independent spec files still run in parallel across workers.
  fullyParallel: false,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

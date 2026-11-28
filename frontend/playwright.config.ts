import { defineConfig, devices } from "@playwright/test";
import { SITE_ORIGIN } from "./e2e/support/app";

export default defineConfig({
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: process.env.CI ? 3 : 1,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["github"]] : [["list"]],
  use: {
    baseURL: SITE_ORIGIN,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    timezoneId: "America/Chicago",
    locale: "en-US",
  },
  projects: [
    { name: "chromium", testDir: "./e2e/journeys", use: { ...devices["Desktop Chrome"] } },
    { name: "sweep-setup", testDir: "./e2e/sweep", testMatch: /\.setup\.ts$/ },
    {
      name: "sweep",
      testDir: "./e2e/sweep",
      testMatch: /\.spec\.ts$/,
      dependencies: ["sweep-setup"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

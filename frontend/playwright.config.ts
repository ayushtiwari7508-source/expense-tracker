import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for the Expense Tracker frontend.
 *
 * Tests run against the REAL application stack:
 *   Chromium → Next.js (webServer) → FastAPI (API_BASE_URL) → PostgreSQL (E2E database)
 *
 * Prerequisites:
 *   - The E2E Postgres database must exist and be migrated (see tests/support/README-SETUP.md)
 *   - The FastAPI backend must be running at API_BASE_URL (default http://127.0.0.1:8000)
 *   - The Next.js frontend is started automatically by Playwright (this webServer block)
 *
 * Environment variables:
 *   API_BASE_URL   – FastAPI base (default http://127.0.0.1:8000)
 *   E2E_BASE_URL   – overrides the Next.js base URL if you run the frontend yourself
 *   CI             – enables retries on CI
 */
const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  // Tests share one test database and create/own their data, so avoid
  // data races between workers. Isolation comes from unique users + contexts.
  fullyParallel: false,
  workers: process.env.CI ? 1 : 2,
  forbidOnly: !!process.env.CI,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  // Keep local runs deterministic; CI retries once and uploads traces.
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Opt-in (E2E_MOBILE=1): WebKit's Playwright build partitions cookies per
    // localhost port, so cookie-authenticated sessions require a same-origin
    // API (the production reverse-proxy pattern) — see README "End-to-end tests".
    ...(process.env.E2E_MOBILE
      ? [
          {
            name: "mobile-safari",
            testIgnore: /responsive\.spec\.ts/,
            use: { ...devices["iPhone 13"] },
          },
        ]
      : []),
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 120_000,
        env: {
          // The app appends route paths to this base, so it must include /api/v1
          // (matches lib/api.ts and the Docker build arg).
          NEXT_PUBLIC_API_URL: `${API_BASE_URL}/api/v1`,
        },
      },
});

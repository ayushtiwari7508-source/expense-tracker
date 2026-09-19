import { test as base, expect } from "@playwright/test";
import {
  assertNoUnexpectedErrors,
  attachAudits,
  Audits,
  cleanupUser,
  registerUser,
} from "./helpers";

/**
 * Extended test fixture.
 *
 *  - `page`   : isolated browser context + page (no shared cookies/storage)
 *  - `audits` : console / page-error / failed-request capture, asserted automatically
 *  - `asUser` : registers a UNIQUE user via the real API, then seeds the browser
 *               session the same way the app's AuthProvider does (localStorage
 *               "et_token") and reloads so the authenticated UI boots with that
 *               user. Tests that need to exercise the login/register UI do so
 *               explicitly with a clean page instead.
 *               Returns { token, email } for API-based setup/teardown.
 */
export const test = base.extend<{
  audits: Audits;
  asUser: { token: string; email: string };
}>({
  audits: async ({ page }, use, testInfo) => {
    const audits = attachAudits(page);
    await use(audits);
    audits.detach();
    // Automatic console/page-error/network audit. Tests that intentionally
    // break the API opt out with "@audit-off" in their title.
    if (testInfo.status === "passed" && !testInfo.title.includes("@audit-off")) {
      assertNoUnexpectedErrors(audits, testInfo);
    }
  },

  asUser: async ({ page, audits }, use) => {
    const { token, user } = await registerUser(page.request);
    await page.addInitScript(
      ([storedToken]) => {
        // Same key the app's ApiClient uses (lib/api.ts TOKEN_KEY).
        window.localStorage.setItem("et_token", storedToken!);
      },
      [token] as [string],
    );
    // First load performs the session hydration the same way the app does.
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await use({ token, email: user.email });
    // Auto-cleanup: best-effort, never masks the real test failure.
    try {
      await cleanupUser(page.request, token);
    } catch {
      /* best effort */
    }
  },
});

// Re-export expect so specs import a single module.
export { expect };

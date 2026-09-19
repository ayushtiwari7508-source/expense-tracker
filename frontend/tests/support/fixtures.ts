import { test as base, expect } from "@playwright/test";
import { assertNoUnexpectedErrors, attachAudits, Audits, cleanupUser, registerUser } from "./helpers";

/**
 * Extended test fixture.
 *
 *  - `page`   : isolated browser context + page (no shared cookies/storage)
 *  - `audits` : console / page-error / failed-request capture, asserted automatically
 *  - `asUser` : registers a UNIQUE user via the real API and logs them in.
 *               Playwright's per-context request shares the cookie jar with
 *               the browser, so the HttpOnly auth cookie set by login
 *               authenticates the page immediately — no localStorage, and no
 *               test ever touches a raw token.
 *               Returns { email } for assertions/cleanup.
 */
export const test = base.extend<{
  audits: Audits;
  asUser: { email: string };
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

  asUser: async ({ page }, use) => {
    const { user } = await registerUser(page.request);
    // First load boots the authenticated UI: the browser sends the cookie,
    // the app restores the session through /auth/me.
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await use({ email: user.email });
    // Auto-cleanup: best-effort, never masks the real test failure.
    try {
      await cleanupUser(page.request);
    } catch {
      /* best effort */
    }
  },
});

// Re-export expect so specs import a single module.
export { expect };

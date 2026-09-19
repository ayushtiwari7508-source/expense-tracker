import { expect } from "@playwright/test";
import { test } from "./support/fixtures";

test.describe("Loading & error states", () => {
  test("slow API keeps the page usable and shows no NaN", async ({ page, asUser }) => {
    await page.route("**/api/v1/expenses*", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 600));
      await route.continue();
    });
    await page.goto("/expenses");
    // A fresh user has no expenses: after the delayed fetch resolves, the
    // intentional empty state must render (not a crash, not NaN).
    await expect(page.getByText("No expenses yet")).toBeVisible({ timeout: 15_000 });
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("NaN");
  });

  test("API failure shows an error state with a retry option @audit-off", async ({ page, audits, asUser }) => {
    await page.route("**/api/v1/expenses*", (route) => route.abort("failed"));
    await page.goto("/expenses");
    await expect(page.getByText("Something went wrong")).toBeVisible();
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();

    // Recovery: unblock the route and retry.
    audits.dismissConsole(
      (t) => t.includes("ERR_FAILED") || t.includes("Failed to fetch") || t.includes("load failed"),
    );
    audits.dismissFailed((url) => url.includes("/api/v1/expenses"));
    await page.unroute("**/api/v1/expenses*");
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByText("No expenses yet")).toBeVisible();
  });
});

test.describe("Responsive layouts", () => {
  const viewports = [
    { width: 390, height: 844, name: "mobile" },
    { width: 768, height: 1024, name: "tablet" },
    { width: 1024, height: 768, name: "laptop" },
    { width: 1440, height: 900, name: "desktop" },
  ];

  for (const vp of viewports) {
    test(`no horizontal overflow at ${vp.width}x${vp.height}`, async ({ page, asUser }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/login");
      await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();

      await page.goto("/expenses");
      await expect(page.getByRole("button", { name: "Add expense" }).first()).toBeVisible();
      await page.goto("/dashboard");
      await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
});

test.describe("Accessibility basics", () => {
  test("form inputs have accessible labels", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();

    await page.goto("/register");
    await expect(page.getByLabel("Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  });

  test("navigation has an accessible name and sign-out is labelled", async ({ page, asUser }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  });

  test("dialog closes with Escape and focus is manageable", async ({ page, asUser }) => {
    await page.goto("/expenses");
    await page.getByRole("button", { name: "Add expense" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Add expense" });
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });
});

import { uniqueEmail, TEST_PASSWORD } from "./support/helpers";
import { test, expect } from "./support/fixtures";

test.describe("Profile / settings", () => {
  test("profile loads with the registered user information", async ({ page }) => {
    const email = uniqueEmail("profile");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Profile Checker");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL(/\/settings/);

    await expect(page.getByLabel("Name")).toHaveValue("Profile Checker");
    await expect(page.getByLabel("Email")).toHaveValue(email);
  });

  test("name update persists after refresh", async ({ page }) => {
    const email = uniqueEmail("profile-update");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Before Update");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByLabel("Name").fill("After Update");
    await page.getByRole("button", { name: "Save profile" }).click();

    await page.reload();
    await expect(page.getByLabel("Name")).toHaveValue("After Update");
    await expect(page.getByLabel("Email")).toHaveValue(email);
  });

  test("empty name is rejected without saving", async ({ page }) => {
    const email = uniqueEmail("profile-invalid");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Valid Name");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole("link", { name: "Settings" }).click();
    await page.getByLabel("Name").fill("");
    await page.getByRole("button", { name: "Save profile" }).click();

    // Either an inline message or the server-side error is surfaced; the profile must not change.
    const feedback = page.locator('[role="alert"], .text-error, [class*="error"]');
    await expect(feedback.first()).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Name")).toHaveValue("Valid Name");
  });
});

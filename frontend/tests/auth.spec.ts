import { uniqueEmail, TEST_PASSWORD } from "./support/helpers";
import { test, expect } from "./support/fixtures";

test.describe("Registration", () => {
  test("valid registration reaches the dashboard", async ({ page, audits }) => {
    const email = uniqueEmail("reg");
    await page.goto("/register");

    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("duplicate email shows a meaningful error", async ({ page }) => {
    const email = uniqueEmail("dup");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.goto("/register");
    await page.getByLabel("Name").fill("Second Attempt");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.locator('p[role="alert"]')).toContainText("already registered");
    await expect(page).toHaveURL(/\/register/);
  });

  test("invalid email and weak password show validation messages", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Name").fill("T");
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Password", { exact: true }).fill("weak");
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByText("Enter your name.")).toBeVisible();
    await expect(page.getByText("Enter a valid email.")).toBeVisible();
    await expect(page.getByText("At least 8 characters.")).toBeVisible();
    await expect(page).toHaveURL(/\/register/);
  });

  test("missing required fields blocks submission", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page.getByText("Enter your name.")).toBeVisible();
    await expect(page.getByText("Enter a valid email.")).toBeVisible();
    await expect(page.getByText("At least 8 characters.")).toBeVisible();
  });

  test("password complexity rules surface specific hints", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(uniqueEmail("pw"));

    await page.getByLabel("Password", { exact: true }).fill("alllowercase1");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Add an uppercase letter.")).toBeVisible();

    await page.getByLabel("Password", { exact: true }).fill("NoDigitsHere");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Add a digit.")).toBeVisible();
  });
});

test.describe("Login", () => {
  test("valid login lands on the dashboard with user info", async ({ page, audits }) => {
    const email = uniqueEmail("login");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    // Sign out to exercise the login page itself.
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("incorrect password shows an error and keeps the user signed out", async ({ page }) => {
    const email = uniqueEmail("wrongpw");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("Definitely-Wrong-1");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.locator('p[role="alert"]')).toContainText("Incorrect email or password.");
    await expect(page).toHaveURL(/\/login/);
  });

  test("nonexistent user is rejected", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(uniqueEmail("ghost"));
    await page.getByLabel("Password").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.locator('p[role="alert"]')).toContainText(/Incorrect email or password/i);
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Logout & protected routes", () => {
  test("logout removes the session and protected routes bounce to login", async ({ page }) => {
    const email = uniqueEmail("logout");
    await page.goto("/register");
    await page.getByLabel("Name").fill("Playwright Test User");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);

    for (const route of ["/dashboard", "/expenses", "/budgets", "/analytics", "/settings"]) {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

import { expect } from "@playwright/test";
import { test } from "./support/fixtures";
import { uniqueEmail, TEST_PASSWORD } from "./support/helpers";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysFromToday = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return iso(d);
};

/** Register a user entirely through the real UI and land on the dashboard. */
async function registerViaUi(page: import("@playwright/test").Page, name: string) {
  const email = uniqueEmail("iso");
  await page.goto("/register");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  return email;
}

test.describe("User isolation", () => {
  test("two users see only their own expenses and budgets", async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    const emailA = await registerViaUi(pageA, "Isolated A");
    const emailB = await registerViaUi(pageB, "Isolated B");

    // Each context's request shares its own cookie jar; no tokens are read.

    // User A creates an expense and a budget through the UI.
    await pageA.goto("/expenses");
    await pageA.getByRole("button", { name: "Add expense" }).first().click();
    let dialog = pageA.getByRole("dialog", { name: "Add expense" });
    await dialog.getByLabel("Amount").fill("1234.50");
    await dialog.getByLabel("Category").selectOption("Food");
    await dialog.getByLabel("Payment method").selectOption("UPI");
    await dialog.getByLabel("Description").fill("A's private lunch");
    await dialog.getByRole("button", { name: "Add expense" }).click();
    await expect(pageA.getByText("A's private lunch")).toBeVisible();

    await pageA.goto("/budgets");
    await pageA.getByRole("button", { name: "New budget" }).click();
    const bDialog = pageA.getByRole("dialog", { name: "New budget" });
    await bDialog.getByLabel("Amount limit").fill("9000");
    await bDialog.getByLabel("Alert threshold (%)").fill("60");
    await bDialog.getByRole("button", { name: "Create budget" }).click();
    await expect(pageA.locator("li").filter({ hasText: "Overall" })).toBeVisible();

    // User B creates their own expense through the UI.
    await pageB.goto("/expenses");
    await pageB.getByRole("button", { name: "Add expense" }).first().click();
    dialog = pageB.getByRole("dialog", { name: "Add expense" });
    await dialog.getByLabel("Amount").fill("777.00");
    await dialog.getByLabel("Category").selectOption("Travel");
    await dialog.getByLabel("Payment method").selectOption("Credit Card");
    await dialog.getByLabel("Description").fill("B's private flight");
    await dialog.getByRole("button", { name: "Add expense" }).click();
    await expect(pageB.getByText("B's private flight")).toBeVisible();

    // ---- Isolation: A must not see B's data, and vice versa --------------
    await pageA.goto("/expenses");
    await expect(pageA.getByText("A's private lunch")).toBeVisible();
    await expect(pageA.getByText("B's private flight")).toHaveCount(0);

    await pageB.goto("/expenses");
    await expect(pageB.getByText("B's private flight")).toBeVisible();
    await expect(pageB.getByText("A's private lunch")).toHaveCount(0);

    await pageB.goto("/budgets");
    await expect(pageB.getByText("No budgets yet")).toBeVisible(); // A's budget is not B's

    // Deleting must also be isolated: B (own cookie jar) cannot delete A's
    // expense by id — the server scopes the lookup to the session user.
    const listA = await (await pageA.request.get(
      `${process.env.API_BASE_URL ?? "http://localhost:8000"}/api/v1/expenses`,
    )).json();
    const expenseAId = listA.items[0].id;
    const forged = await pageB.request.delete(
      `${process.env.API_BASE_URL ?? "http://localhost:8000"}/api/v1/expenses/${expenseAId}`,
    );
    expect([401, 403, 404]).toContain(forged.status());
    await pageA.goto("/expenses");
    await expect(pageA.getByText("A's private lunch")).toBeVisible(); // still there

    // Cleanup both users (each jar cleans its own session's data).
    const { cleanupUser } = await import("./support/helpers");
    await cleanupUser(pageA.request);
    await cleanupUser(pageB.request);
    await contextA.close();
    await contextB.close();
  });
});

test.describe("Full user journey", () => {
  test("register → expense → budget → threshold alert → dashboard → logout", async ({ page }) => {
    // 1. Register through the UI.
    await registerViaUi(page, "Journey User");

    // 2. Create a ₹5,000 overall budget (threshold 50%).
    await page.goto("/budgets");
    await page.getByRole("button", { name: "New budget" }).click();
    const bDialog = page.getByRole("dialog", { name: "New budget" });
    await bDialog.getByLabel("Amount limit").fill("5000");
    await bDialog.getByLabel("Alert threshold (%)").fill("50");
    await bDialog.getByRole("button", { name: "Create budget" }).click();
    // Deterministic: the budget row must exist before moving on.
    await expect(
      page.locator("li").filter({ hasText: "Overall" }).filter({ hasText: "₹5,000.00" }),
    ).toBeVisible();

    // 3. Create two expenses (₹2,000 + ₹1,500 ⇒ 70% ⇒ warning).
    for (const [amount, desc] of [
      ["2000", "Journey groceries"],
      ["1500", "Journey fuel"],
    ]) {
      await page.goto("/expenses");
      await page.getByRole("button", { name: "Add expense" }).first().click();
      const dialog = page.getByRole("dialog", { name: "Add expense" });
      await dialog.getByLabel("Amount").fill(amount);
      await dialog.getByLabel("Category").selectOption("Food");
      await dialog.getByLabel("Payment method").selectOption("UPI");
      await dialog.getByLabel("Description").fill(desc);
      await dialog.getByRole("button", { name: "Add expense" }).click();
      await expect(page.getByText(desc)).toBeVisible();
    }

    // 4. Budget utilization reflects ₹3,500 of ₹5,000 (70%).
    await page.goto("/budgets");
    const utilRow = page.locator("li").filter({ hasText: "Overall" });
    await expect(utilRow).toContainText("₹3,500.00");
    await expect(utilRow).toContainText("of ₹5,000.00");
    await expect(utilRow).toContainText("70% used");

    // 5. An alert was generated and is visible.
    await page.getByRole("link", { name: "Alerts" }).click();
    await expect(page.getByText("Budget warning").first()).toBeVisible();

    // 6. Dashboard aggregates the same data.
    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(page.getByText("₹3,500.00").first()).toBeVisible();

    // 7. Settings shows the journey user; logout returns to login.
    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page.getByLabel("Name")).toHaveValue("Journey User");
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});

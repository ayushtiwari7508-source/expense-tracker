import { expect } from "@playwright/test";
import { test } from "./support/fixtures";
import { createBudgetApi, createExpenseApi } from "./support/helpers";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysFromToday = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return iso(d);
};

/** Budget ₹1,000 @ 50% threshold + ₹800 spending ⇒ 80% ⇒ WARNING alert. */
async function seedThresholdCrossing(page: import("@playwright/test").Page) {
  await createBudgetApi(page.request, {
    amount: 1000,
    start_date: daysFromToday(0),
    end_date: daysFromToday(30),
    alert_threshold: 50,
  });
  await createExpenseApi(page.request, {
    amount: 800,
    category: "Food",
    payment_method: "UPI",
    description: "E2E threshold expense",
    expense_date: daysFromToday(0),
  });
  // Budget reads evaluate alerts server-side, so visit budgets once.
  await page.goto("/budgets");
  const utilRow = page.locator("li").filter({ hasText: "Overall" });
  await expect(utilRow).toContainText("80% used");
  return utilRow;
}

test.describe("Alerts", () => {
  test("crossing the budget threshold generates a warning alert", async ({ page, asUser }) => {
    await seedThresholdCrossing(page);

    await page.getByRole("link", { name: "Alerts" }).click();
    await expect(page).toHaveURL(/\/alerts/);

    await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
    await expect(page.getByText(/unread alert/i).first()).toBeVisible();
    await expect(page.getByText("Budget warning").first()).toBeVisible();
    await expect(page.getByText("Unread", { exact: true }).first()).toBeVisible();
  });

  test("marking an alert as read clears its unread state", async ({ page, asUser }) => {
    await seedThresholdCrossing(page);

    await page.getByRole("link", { name: "Alerts" }).click();
    const alertItem = page.locator("li").filter({ hasText: "Budget warning" });
    await expect(alertItem.first()).toBeVisible();

    await alertItem.first().getByRole("button", { name: "Mark read" }).click();
    await expect(alertItem.first().getByText("Unread")).toHaveCount(0);
    await expect(alertItem.first().getByRole("button", { name: "Mark read" })).toHaveCount(0);
    await expect(page.getByText("You're all caught up.")).toBeVisible();
  });

  test("mark all read clears every unread alert", async ({ page, asUser }) => {
    await seedThresholdCrossing(page);

    await page.getByRole("link", { name: "Alerts" }).click();
    await expect(page.getByText("Unread", { exact: true }).first()).toBeVisible();

    await page.getByRole("button", { name: "Mark all read" }).click();
    await expect(page.getByText("All alerts marked as read.")).toBeVisible(); // toast
    await expect(page.getByText("You're all caught up.")).toBeVisible();
    await expect(page.getByText("Unread", { exact: true })).toHaveCount(0);
  });

  test("no alerts shows an intentional empty state", async ({ page, asUser }) => {
    await page.goto("/alerts");
    await expect(page.getByText("No alerts yet")).toBeVisible();
    await expect(page.getByText("You're all caught up.")).toBeVisible();
  });
});

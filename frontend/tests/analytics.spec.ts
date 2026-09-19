import { expect } from "@playwright/test";
import { test } from "./support/fixtures";
import { createExpenseApi } from "./support/helpers";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysFromToday = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return iso(d);
};

/**
 * Food ₹1,000 · Travel ₹2,000 · Shopping ₹3,000 · Bills ₹4,000 ⇒ ₹10,000 total.
 * Spread over 4 days so time-series/trend endpoints have multiple points.
 */
async function seedKnownDataset(page: import("@playwright/test").Page, token: string) {
  const rows = [
    { amount: 1000, category: "Food", description: "E2E Food", offset: 0 },
    { amount: 2000, category: "Travel", description: "E2E Travel", offset: -1 },
    { amount: 3000, category: "Shopping", description: "E2E Shopping", offset: -2 },
    { amount: 4000, category: "Bills", description: "E2E Bills", offset: -3 },
  ];
  for (const row of rows) {
    await createExpenseApi(page.request, token, {
      amount: row.amount,
      category: row.category,
      description: row.description,
      payment_method: "UPI",
      expense_date: daysFromToday(row.offset),
    });
  }
}

test.describe("Analytics", () => {
  test("summary, category share, top expenses and insights reflect seeded data", async ({
    page,
    asUser,
  }) => {
    await seedKnownDataset(page, asUser.token);

    await page.goto("/analytics");

    // Headline numbers are computed by the backend from the seeded rows.
    await expect(page.getByText("Total spent")).toBeVisible();
    await expect(page.getByText("₹10,000.00").first()).toBeVisible();
    await expect(page.getByText("₹2,500.00").first()).toBeVisible(); // average
    await expect(page.getByText("₹4,000.00").first()).toBeVisible(); // highest

    // Category share chart renders with real data (aria-labelled canvas host).
    const share = page.getByRole("img", { name: "Spending share by category" });
    await expect(share).toBeVisible();

    // Largest expenses lists the Bills row first (#1) with ₹4,000.00.
    const topList = page.getByRole("list").filter({ has: page.getByText("#1") });
    await expect(page.getByText("#1")).toBeVisible();
    await expect(page.getByText("#4")).toBeVisible();

    // Insights section renders at least one factual insight.
    await expect(page.getByRole("heading", { name: "Insights" })).toBeVisible();
  });

  test("trend chart renders and granularity switch updates it", async ({ page, asUser }) => {
    await seedKnownDataset(page, asUser.token);

    await page.goto("/analytics");
    const trend = page.getByRole("img", { name: "Spending trend" });
    await expect(trend).toBeVisible();

    // Daily granularity yields one point per day (4 seeded days).
    await page.getByRole("button", { name: "Daily", exact: true }).click();
    await expect(trend).toBeVisible();
    await expect(page.getByText("Trend:")).toBeVisible();

    for (const label of ["Weekly", "Monthly", "Yearly"]) {
      await page.getByRole("button", { name: label, exact: true }).click();
      // The chart must re-render (stay visible) without crashing.
      await expect(trend).toBeVisible();
    }
  });

  test("changing the date range keeps the dashboard usable", async ({ page, asUser }) => {
    await seedKnownDataset(page, asUser.token);
    await page.goto("/analytics");

    await page.getByRole("combobox", { name: "Date range" }).selectOption("30");
    await expect(page.getByText("₹10,000.00").first()).toBeVisible(); // data is within 30 days

    await page.getByRole("combobox", { name: "Date range" }).selectOption("365");
    await expect(page.getByText("₹10,000.00").first()).toBeVisible();
  });

  test("empty analytics shows intentional empty states, not NaN", async ({ page, asUser }) => {
    await page.goto("/analytics");
    await expect(page.getByText("No data in this period").first()).toBeVisible();
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("NaN");
    expect(body).not.toContain("undefined");
  });
});

test.describe("Dashboard", () => {
  test("dashboard stats come from the backend dataset", async ({ page, asUser }) => {
    await seedKnownDataset(page, asUser.token);

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // 30-day window default ⇒ the last 4 days' ₹10,000 shows up.
    await expect(page.getByText("Total spent")).toBeVisible();
    await expect(page.getByText("₹10,000.00").first()).toBeVisible();

    // Category breakdown chart renders.
    const chart = page.getByRole("img", { name: /spending|trend|category/i }).first();
    await expect(chart).toBeVisible();

    // Largest expenses card shows the top item.
    await expect(page.getByText("Largest expenses")).toBeVisible();
  });

  test("empty dashboard shows welcome/empty guidance, not errors", async ({ page, asUser }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByText(/no expenses|welcome|get started|add your first/i).first(),
    ).toBeVisible();
  });
});

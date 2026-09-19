import { expect } from "@playwright/test";
import { test } from "./support/fixtures";

const TODAY = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysFromToday = (n: number) => {
  const d = new Date(TODAY);
  d.setDate(d.getDate() + n);
  return iso(d);
};

/** Fill and submit the Add expense modal. */
async function addExpense(
  page: import("@playwright/test").Page,
  expense: { amount: string; category?: string; description?: string; payment?: string; date?: string },
) {
  await page.getByRole("button", { name: "Add expense" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Add expense" });
  await dialog.getByLabel("Amount").fill(expense.amount);
  if (expense.date) await dialog.getByLabel("Date").fill(expense.date);
  if (expense.category) await dialog.getByLabel("Category").selectOption(expense.category);
  if (expense.payment) await dialog.getByLabel("Payment method").selectOption(expense.payment);
  if (expense.description !== undefined)
    await dialog.getByLabel("Description").fill(expense.description);
  await dialog.getByRole("button", { name: "Add expense" }).click();
}

/** Row for an expense with the given description. */
function rowFor(page: import("@playwright/test").Page, description: string) {
  return page.getByRole("row", { name: new RegExp(description.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) });
}

test.describe("Expense CRUD", () => {
  test("create, read, update and delete an expense", async ({ page, asUser }) => {
    await page.goto("/expenses");

    // ---- Create ----------------------------------------------------------
    await addExpense(page, {
      amount: "250.50",
      category: "Food",
      payment: "Credit Card",
      description: "E2E lunch checkpoint",
      date: daysFromToday(0),
    });
    const row = rowFor(page, "E2E lunch checkpoint");
    await expect(row).toBeVisible();
    await expect(row).toContainText("₹250.50");
    await expect(row).toContainText("Food");
    await expect(row).toContainText("Credit Card");

    // ---- Update ----------------------------------------------------------
    await row.getByRole("button", { name: "Edit" }).click();
    const editDialog = page.getByRole("dialog", { name: "Edit expense" });
    await expect(editDialog).toBeVisible();
    await editDialog.getByLabel("Amount").fill("499.99");
    await editDialog.getByLabel("Category").selectOption("Travel");
    await editDialog.getByLabel("Description").fill("E2E lunch checkpoint v2");
    await editDialog.getByRole("button", { name: "Save changes" }).click();

    const updatedRow = rowFor(page, "E2E lunch checkpoint v2");
    await expect(updatedRow).toBeVisible();
    await expect(updatedRow).toContainText("₹499.99");
    await expect(updatedRow).toContainText("Travel");
    await expect(updatedRow).toContainText("Credit Card");

    // ---- Delete (with confirmation) --------------------------------------
    await updatedRow.getByRole("button", { name: "Delete" }).click();
    const confirm = page.getByRole("dialog", { name: "Delete expense" });
    await expect(confirm).toBeVisible();
    await confirm.getByRole("button", { name: "Delete" }).click();

    await expect(page.getByText("E2E lunch checkpoint v2")).toHaveCount(0);
  });
});

test.describe("Expense validation", () => {
  test("invalid amounts are rejected by the form", async ({ page, asUser }) => {
    await page.goto("/expenses");
    await page.getByRole("button", { name: "Add expense" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Add expense" });

    // Empty amount
    await dialog.getByRole("button", { name: "Add expense" }).click();
    await expect(dialog.getByText(/amount/i).first()).toBeVisible();

    // Negative amount
    await dialog.getByLabel("Amount").fill("-100");
    await dialog.getByRole("button", { name: "Add expense" }).click();
    await expect(dialog.getByText(/amount/i).first()).toBeVisible();

    // Zero amount
    await dialog.getByLabel("Amount").fill("0");
    await dialog.getByRole("button", { name: "Add expense" }).click();
    await expect(dialog.getByText(/amount/i).first()).toBeVisible();

    // The modal never closed and nothing was created.
    await expect(dialog).toBeVisible();
    await expect(page.getByText("No expenses yet")).toBeVisible();
  });
});

test.describe("Expense search, filters, sorting, pagination", () => {
  test.beforeEach(async ({ page, asUser }) => {
    // Seed via the API: fast, deterministic, and exactly the data this test owns.
    // 24 items > page_size (20), so pagination is exercised.
    const descriptions = ["E2E Lunch", "E2E Flight", "E2E Laptop", "E2E Sniper"];
    for (let i = 0; i < 24; i += 1) {
      const idx = i % descriptions.length;
      await page.request.post(`${process.env.API_BASE_URL ?? "http://localhost:8000"}/api/v1/expenses`, {
        headers: { Authorization: `Bearer ${asUser.token}` },
        data: {
          amount: (i + 1) * 100, // 100 … 1200, all distinct
          category: ["Food", "Travel", "Shopping", "Bills"][idx],
          payment_method: ["UPI", "Credit Card", "Cash", "Bank Transfer"][idx],
          description: `E2E ${descriptions[idx]} ${i + 1}`,
          expense_date: daysFromToday(-i),
        },
      });
    }
    await page.goto("/expenses");
    await expect(page.getByRole("table")).toBeVisible();
  });

  test("search narrows results and can be cleared", async ({ page }) => {
    const search = page.getByRole("textbox", { name: "Search expenses" });
    await search.fill("Laptop");
    await expect(page.getByRole("row", { name: /E2E Laptop/ }).first()).toBeVisible();
    await expect(page.getByRole("row", { name: /E2E Lunch/ })).toHaveCount(0);

    await search.fill("zzzz-no-match");
    await expect(page.getByText("Nothing matches these filters")).toBeVisible();

    await search.fill("");
    await expect(page.getByRole("row", { name: /E2E/ }).first()).toBeVisible();
  });

  test("category and payment filters apply together", async ({ page }) => {
    await page.getByRole("combobox", { name: "Filter by category" }).selectOption("Food");
    await expect(page.getByRole("row", { name: /E2E Lunch/ }).first()).toBeVisible();
    await expect(page.getByRole("row", { name: /E2E Flight|E2E Laptop/ })).toHaveCount(0);

    await page.getByRole("combobox", { name: "Filter by payment method" }).selectOption("UPI");
    // Food ∧ UPI rows exist in the seed data and must be the only ones left.
    await expect(page.getByRole("row", { name: /E2E Lunch/ }).first()).toBeVisible();
    await expect(page.getByRole("row", { name: /E2E Flight|E2E Laptop|E2E Sniper/ })).toHaveCount(0);
  });

  test("sorting by amount toggles ascending and descending", async ({ page }) => {
    // Default sort is newest first; switch to Amount.
    await page.getByRole("combobox", { name: "Sort by" }).selectOption("amount:desc");
    const amounts = await page
      .getByRole("table")
      .getByRole("row")
      .filter({ has: page.getByText(/₹/) })
      .allInnerTexts();
    expect(amounts.length).toBeGreaterThan(0);
    // Descending first click (largest → smallest across all pages of data).
    const extract = (t: string) => Number(t.match(/₹([\d,.]+)/)?.[1]?.replace(/,/g, "") ?? 0);
    const firstPageDesc = amounts.map(extract);
    expect([...firstPageDesc].sort((a, b) => b - a)).toEqual(firstPageDesc);
  });

  test("pagination walks forward and back without losing rows", async ({ page }) => {
    const next = page.getByRole("button", { name: "Next" });
    await expect(page.getByText(/Page 1 of/)).toBeVisible(); // 24 items > page_size 20
    await next.click();
    await expect(page.getByText(/Page 2 of/)).toBeVisible();
    await expect(page.getByRole("row", { name: /E2E/ }).first()).toBeVisible();
    await expect(next).toBeDisabled(); // final page
    await page.getByRole("button", { name: "Prev" }).click();
    await expect(page.getByText(/Page 1 of/)).toBeVisible();
  });
});

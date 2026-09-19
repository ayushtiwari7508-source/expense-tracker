import { expect } from "@playwright/test";
import { test } from "./support/fixtures";
import { createBudgetApi, createExpenseApi } from "./support/helpers";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const daysFromToday = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return iso(d);
};

async function openBudgetDialog(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "New budget" }).click();
  return page.getByRole("dialog", { name: "New budget" });
}

test.describe("Budgets", () => {
  test("create, utilization integration, edit, delete", async ({ page, asUser }) => {
    const api = process.env.API_BASE_URL ?? "http://localhost:8000";

    await page.goto("/budgets");

    // ---- Create: overall budget ₹10,000, alert threshold 50% -------------
    const dialog = await openBudgetDialog(page);
    await dialog.getByLabel("Amount limit").fill("10000");
    await dialog.getByLabel("Alert threshold (%)").fill("50");
    await dialog.getByRole("button", { name: "Create budget" }).click();
    // Wait for the created budget row (POST + list refresh), not just any text.
    await expect(page.locator("li").filter({ hasText: "Overall" })).toBeVisible();

    // ---- Integration: ₹4,000 expense ⇒ 40% used, ₹6,000 left -------------
    const res = await page.request.post(`${api}/api/v1/expenses`, {
      data: {
        amount: 4000,
        category: "Shopping",
        payment_method: "Credit Card",
        description: "E2E integration expense",
        expense_date: daysFromToday(0),
      },
    });
    expect(res.ok()).toBeTruthy();

    await page.reload();
    const utilRow = page
      .locator("li")
      .filter({ hasText: "Overall" })
      .filter({ hasText: "₹10,000.00" });
    await expect(utilRow).toBeVisible();
    await expect(utilRow).toContainText("₹4,000.00");
    await expect(utilRow).toContainText("of ₹10,000.00");
    await expect(utilRow).toContainText("40% used");
    await expect(utilRow).toContainText("₹6,000.00 left");
    await expect(utilRow).toContainText("NORMAL");

    // ---- Edit: raise the limit, verify new numbers -----------------------
    await utilRow.getByRole("button", { name: "Edit" }).click();
    const editDialog = page.getByRole("dialog", { name: "Edit budget" });
    await expect(editDialog).toBeVisible();
    await editDialog.getByLabel("Amount limit").fill("12000");
    await editDialog.getByRole("button", { name: "Save changes" }).click();
    const editedRow = page
      .locator("li")
      .filter({ hasText: "Overall" })
      .filter({ hasText: "₹12,000.00" });
    await expect(editedRow).toContainText("₹4,000.00");
    await expect(editedRow).toContainText("of ₹12,000.00");

    // ---- Delete with confirmation ----------------------------------------
    await editedRow.getByRole("button", { name: "Delete" }).click();
    const confirm = page.getByRole("dialog", { name: "Delete budget" });
    await expect(confirm).toBeVisible();
    await confirm.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText("No budgets yet")).toBeVisible();
  });

  test("second expense updates utilization", async ({ page, asUser }) => {
    await createBudgetApi(page.request, {
      amount: 10000,
      start_date: daysFromToday(0),
      end_date: daysFromToday(30),
      alert_threshold: 50,
    });
    await createExpenseApi(page.request, {
      amount: 4000,
      category: "Shopping",
      payment_method: "Credit Card",
      description: "E2E util 1",
      expense_date: daysFromToday(0),
    });
    await page.goto("/budgets");
    const row = page.locator("li").filter({ hasText: "Overall" });
    await expect(row).toContainText("40% used");

    await createExpenseApi(page.request, {
      amount: 3000,
      category: "Food",
      payment_method: "UPI",
      description: "E2E util 2",
      expense_date: daysFromToday(0),
    });
    await page.reload();
    await expect(row).toContainText("70% used");
  });

  test("validation rejects non-positive and missing amounts", async ({ page, asUser }) => {
    await page.goto("/budgets");
    const dialog = await openBudgetDialog(page);

    await dialog.getByLabel("Amount limit").fill("0");
    await dialog.getByRole("button", { name: "Create budget" }).click();
    await expect(dialog.getByText(/amount/i).first()).toBeVisible();
    await expect(dialog).toBeVisible();

    await dialog.getByLabel("Amount limit").fill("-500");
    await dialog.getByRole("button", { name: "Create budget" }).click();
    await expect(dialog.getByText(/amount/i).first()).toBeVisible();

    // Nothing was created.
    await page.keyboard.press("Escape");
    await expect(page.getByText("No budgets yet")).toBeVisible();
  });
});

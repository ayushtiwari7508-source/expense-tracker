"use client";

import { useState, type FormEvent } from "react";
import { Button, Field, Input, Select, Textarea } from "./ui";
import { EXPENSE_CATEGORIES, PAYMENT_METHODS, type Expense } from "@/lib/types";
import { todayISO } from "@/lib/format";

export interface ExpenseFormValues {
  amount: number;
  category: string;
  description: string | null;
  payment_method: string;
  expense_date: string;
}

export function ExpenseForm({
  initial,
  submitting,
  onSubmit,
  onCancel,
}: {
  initial?: Expense;
  submitting: boolean;
  onSubmit: (values: ExpenseFormValues) => void;
  onCancel: () => void;
}) {
  const [amount, setAmount] = useState(initial ? String(initial.amount) : "");
  const [category, setCategory] = useState(initial?.category ?? "Food");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [paymentMethod, setPaymentMethod] = useState(initial?.payment_method ?? "UPI");
  const [expenseDate, setExpenseDate] = useState(initial?.expense_date ?? todayISO());
  const [errors, setErrors] = useState<Record<string, string>>({});

  function onSubmit_(event: FormEvent) {
    event.preventDefault();
    const next: Record<string, string> = {};
    const parsed = Number(amount);
    if (!amount || Number.isNaN(parsed) || parsed <= 0) next.amount = "Enter an amount greater than 0.";
    if (parsed > 9_999_999_999) next.amount = "Amount is too large.";
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    onSubmit({
      amount: parsed,
      category,
      description: description.trim() ? description.trim() : null,
      payment_method: paymentMethod,
      expense_date: expenseDate,
    });
  }

  return (
    <form onSubmit={onSubmit_} className="flex flex-col gap-4" noValidate>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Amount" htmlFor="amount" error={errors.amount}>
          <Input
            id="amount"
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="250.50"
          />
        </Field>
        <Field label="Date" htmlFor="expense_date">
          <Input
            id="expense_date"
            type="date"
            required
            value={expenseDate}
            onChange={(event) => setExpenseDate(event.target.value)}
          />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Category" htmlFor="category">
          <Select id="category" value={category} onChange={(event) => setCategory(event.target.value)}>
            {EXPENSE_CATEGORIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Payment method" htmlFor="payment_method">
          <Select
            id="payment_method"
            value={paymentMethod}
            onChange={(event) => setPaymentMethod(event.target.value)}
          >
            {PAYMENT_METHODS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Field label="Description" htmlFor="description" hint="Optional">
        <Textarea
          id="description"
          maxLength={255}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Dinner with friends"
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          {initial ? "Save changes" : "Add expense"}
        </Button>
      </div>
    </form>
  );
}

"use client";

import { useState, type FormEvent } from "react";
import { Button, Field, Input, Select } from "./ui";
import { EXPENSE_CATEGORIES, type Budget } from "@/lib/types";

export interface BudgetFormValues {
  category: string | null;
  amount: number;
  start_date: string;
  end_date: string;
  alert_threshold: number;
}

function monthStart(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function monthEnd(): string {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
}

export function BudgetForm({
  initial,
  submitting,
  onSubmit,
  onCancel,
}: {
  initial?: Budget;
  submitting: boolean;
  onSubmit: (values: BudgetFormValues) => void;
  onCancel: () => void;
}) {
  const [category, setCategory] = useState(initial?.category ?? "");
  const [amount, setAmount] = useState(initial ? String(initial.amount) : "");
  const [startDate, setStartDate] = useState(initial?.start_date ?? monthStart());
  const [endDate, setEndDate] = useState(initial?.end_date ?? monthEnd());
  const [threshold, setThreshold] = useState(initial ? String(initial.alert_threshold) : "80");
  const [errors, setErrors] = useState<Record<string, string>>({});

  function onSubmit_(event: FormEvent) {
    event.preventDefault();
    const next: Record<string, string> = {};

    const parsedAmount = Number(amount);
    if (!amount || Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      next.amount = "Enter an amount greater than 0.";
    }
    const parsedThreshold = Number(threshold);
    if (threshold === "" || Number.isNaN(parsedThreshold) || parsedThreshold < 0 || parsedThreshold > 100) {
      next.alert_threshold = "Enter a value between 0 and 100.";
    }
    if (startDate && endDate && startDate > endDate) {
      next.end_date = "End date must be on or after the start date.";
    }
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    onSubmit({
      category: category === "" ? null : category,
      amount: parsedAmount,
      start_date: startDate,
      end_date: endDate,
      alert_threshold: parsedThreshold,
    });
  }

  return (
    <form onSubmit={onSubmit_} className="flex flex-col gap-4" noValidate>
      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Category"
          htmlFor="budget-category"
          hint="Empty means all categories."
        >
          <Select
            id="budget-category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">Overall (all categories)</option>
            {EXPENSE_CATEGORIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Amount limit" htmlFor="budget-amount" error={errors.amount}>
          <Input
            id="budget-amount"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            required
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="5000"
          />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Start date" htmlFor="budget-start">
          <Input
            id="budget-start"
            type="date"
            required
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </Field>
        <Field label="End date" htmlFor="budget-end" error={errors.end_date}>
          <Input
            id="budget-end"
            type="date"
            required
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </Field>
      </div>
      <Field
        label="Alert threshold (%)"
        htmlFor="budget-threshold"
        error={errors.alert_threshold}
        hint="Warn when spending reaches this share of the limit."
      >
        <Input
          id="budget-threshold"
          type="number"
          min="0"
          max="100"
          step="1"
          required
          value={threshold}
          onChange={(event) => setThreshold(event.target.value)}
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          {initial ? "Save changes" : "Create budget"}
        </Button>
      </div>
    </form>
  );
}

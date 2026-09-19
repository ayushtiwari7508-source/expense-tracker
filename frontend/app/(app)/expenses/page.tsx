"use client";

import { useCallback, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Plus, Search } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Modal, ConfirmDialog } from "@/components/Modal";
import { ExpenseForm, type ExpenseFormValues } from "@/components/ExpenseForm";
import { Badge, Button, Card, Input, Select } from "@/components/ui";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/states";
import { expenseApi } from "@/lib/api";
import { money, shortDate } from "@/lib/format";
import { useToast } from "@/lib/toast-context";
import { EXPENSE_CATEGORIES, PAYMENT_METHODS, type Expense } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";

const SORTABLE = [
  { value: "expense_date", label: "Date" },
  { value: "amount", label: "Amount" },
  { value: "category", label: "Category" },
  { value: "payment_method", label: "Payment method" },
] as const;

// Sortable table header: shows direction on the active column and exposes
// the state to assistive tech via aria-sort.
function SortHeader({
  label,
  field,
  sortBy,
  sortOrder,
  onToggle,
  align = "left",
  className = "",
}: {
  label: string;
  field: string;
  sortBy: string;
  sortOrder: "asc" | "desc";
  onToggle: (field: string) => void;
  align?: "left" | "right";
  className?: string;
}) {
  const active = sortBy === field;
  return (
    <th
      aria-sort={active ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}
      className={`px-4 py-2.5 font-medium ${align === "right" ? "text-right" : "text-left"} ${className}`}
    >
      <button
        type="button"
        onClick={() => onToggle(field)}
        className={`inline-flex items-center gap-0.5 ${active ? "text-foreground" : "hover:text-foreground"}`}
      >
        {label}
        {/* Fixed-width slot prevents column shift when the arrow appears. */}
        <span aria-hidden className="w-2.5 text-center text-[10px] leading-none">
          {active ? (sortOrder === "asc" ? "↑" : "↓") : ""}
        </span>
      </button>
    </th>
  );
}

export default function ExpensesPage() {
  const toast = useToast();

  // ---------------------------------------------------------------- filters
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [sortBy, setSortBy] = useState("expense_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const query = useMemo(
    () => ({
      page,
      page_size: 20,
      search: search || undefined,
      category: category || undefined,
      payment_method: paymentMethod || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [page, search, category, paymentMethod, sortBy, sortOrder],
  );
  const queryKey = JSON.stringify(query);

  const list = useFetch(
    useCallback(() => expenseApi.list(query), [queryKey]), // eslint-disable-line react-hooks/exhaustive-deps
    queryKey,
  );

  function updateFilter(setter: (value: string) => void) {
    return (value: string) => {
      setter(value);
      setPage(1);
    };
  }

  function toggleSort(field: string) {
    if (sortBy === field) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  }

  // ------------------------------------------------------------- mutations
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<Expense | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  async function saveExpense(values: ExpenseFormValues) {
    setSaving(true);
    try {
      if (editing) {
        await expenseApi.update(editing.id, values);
        toast.success("Expense updated.");
      } else {
        await expenseApi.create(values);
        toast.success("Expense added.");
      }
      setFormOpen(false);
      setEditing(null);
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the expense.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    setDeleteLoading(true);
    try {
      await expenseApi.remove(deleting.id);
      toast.success("Expense deleted.");
      setDeleting(null);
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not delete the expense.");
    } finally {
      setDeleteLoading(false);
    }
  }

  const items = list.data?.items ?? [];
  const total = list.data?.total ?? 0;
  const pages = list.data?.pages ?? 1;

  return (
    <>
      <PageHeader
        title="Expenses"
        description={`${total} expense${total === 1 ? "" : "s"} recorded`}
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Add expense
          </Button>
        }
      />

      {/* Filter row — flat, no card wrapper */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative flex-1 sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle"
            aria-hidden
          />
          <Input
            aria-label="Search expenses"
            placeholder="Search description or category"
            value={search}
            onChange={(event) => updateFilter(setSearch)(event.target.value)}
            className="pl-8"
          />
        </div>
        <Select
          aria-label="Filter by category"
          value={category}
          onChange={(event) => updateFilter(setCategory)(event.target.value)}
          className="w-36"
        >
          <option value="">All categories</option>
          {EXPENSE_CATEGORIES.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Filter by payment method"
          value={paymentMethod}
          onChange={(event) => updateFilter(setPaymentMethod)(event.target.value)}
          className="w-40"
        >
          <option value="">All payment methods</option>
          {PAYMENT_METHODS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Sort by"
          value={`${sortBy}:${sortOrder}`}
          onChange={(event) => {
            const [field, order] = event.target.value.split(":");
            setSortBy(field);
            setSortOrder(order as "asc" | "desc");
          }}
          className="w-44"
        >
          {SORTABLE.map((option) => (
            <optgroup key={option.value} label={option.label}>
              <option value={`${option.value}:desc`}>{option.label} ↓</option>
              <option value={`${option.value}:asc`}>{option.label} ↑</option>
            </optgroup>
          ))}
        </Select>
      </div>

      <Card>
        {list.loading ? (
          <ListSkeleton rows={8} />
        ) : list.error ? (
          <ErrorState message={list.error} onRetry={list.retry} />
        ) : items.length === 0 ? (
          <EmptyState
            title={total === 0 && !search && !category ? "No expenses yet" : "Nothing matches these filters"}
            description={
              total === 0 && !search && !category
                ? "Add your first expense to start tracking."
                : "Try clearing the search or filters."
            }
            action={
              total === 0 && !search && !category ? (
                <Button size="sm" onClick={() => setFormOpen(true)}>
                  <Plus className="h-4 w-4" aria-hidden />
                  Add expense
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                  <SortHeader label="Date" field="expense_date" sortBy={sortBy} sortOrder={sortOrder} onToggle={toggleSort} />
                  <SortHeader label="Category" field="category" sortBy={sortBy} sortOrder={sortOrder} onToggle={toggleSort} />
                  <th className="px-4 py-2.5 font-medium">Description</th>
                  <SortHeader label="Paid with" field="payment_method" sortBy={sortBy} sortOrder={sortOrder} onToggle={toggleSort} className="hidden lg:table-cell" />
                  <SortHeader label="Amount" field="amount" sortBy={sortBy} sortOrder={sortOrder} onToggle={toggleSort} align="right" />
                  <th className="px-4 py-2.5">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((expense) => (
                  <tr key={expense.id} className="hover:bg-background/60">
                    <td className="tnum whitespace-nowrap px-4 py-3 text-foreground">
                      {shortDate(expense.expense_date)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge>{expense.category}</Badge>
                    </td>
                    <td className="hidden max-w-[220px] truncate px-4 py-3 text-muted md:table-cell">
                      {expense.description ?? "—"}
                    </td>
                    <td className="hidden px-4 py-3 text-muted lg:table-cell">
                      {expense.payment_method}
                    </td>
                    <td className="tnum px-4 py-3 text-right font-medium text-foreground">
                      {money(expense.amount)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          setEditing(expense);
                          setFormOpen(true);
                        }}
                        className="mr-3 text-xs font-medium text-primary hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleting(expense)}
                        className="text-xs font-medium text-error hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!list.loading && !list.error && pages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <p className="tnum text-xs text-muted">
              Page {page} of {pages}
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft className="h-4 w-4" aria-hidden />
                Prev
              </Button>
              <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                Next
                <ChevronRight className="h-4 w-4" aria-hidden />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Create / edit modal */}
      <Modal
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        title={editing ? "Edit expense" : "Add expense"}
      >
        <ExpenseForm
          initial={editing ?? undefined}
          submitting={saving}
          onSubmit={saveExpense}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
        />
      </Modal>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        loading={deleteLoading}
        title="Delete expense"
        message={
          deleting
            ? `Delete the ${deleting.category} expense of ${money(deleting.amount)} from ${shortDate(deleting.expense_date)}? This cannot be undone.`
            : ""
        }
      />
    </>
  );
}

"use client";

import { useCallback, useState } from "react";
import { Plus } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Modal, ConfirmDialog } from "@/components/Modal";
import { BudgetForm, type BudgetFormValues } from "@/components/BudgetForm";
import { Badge, Button, Card } from "@/components/ui";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/states";
import { budgetApi } from "@/lib/api";
import { money, mediumDate } from "@/lib/format";
import { useToast } from "@/lib/toast-context";
import type { Budget } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";

const STATUS_TONE = {
  NORMAL: "success",
  WARNING: "warning",
  EXCEEDED: "error",
} as const;

function UtilizationBar({ budget }: { budget: Budget }) {
  const util = budget.utilization;
  const width = Math.min(100, util.utilization_percentage);
  const barColor =
    util.status === "EXCEEDED" ? "bg-error" : util.status === "WARNING" ? "bg-warning" : "bg-success";
  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">
            {budget.category ?? "Overall"}
            <span className="ml-2 text-xs font-normal text-muted">
              {mediumDate(budget.start_date)} – {mediumDate(budget.end_date)}
            </span>
          </p>
        </div>
        <Badge tone={STATUS_TONE[util.status]}>{util.status}</Badge>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded bg-background" role="presentation">
        <div className={`h-full rounded ${barColor}`} style={{ width: `${width}%` }} />
      </div>
      <div className="tnum mt-1.5 flex flex-wrap items-center gap-x-3 text-xs text-muted">
        <span className="font-medium text-foreground">{money(util.amount_spent)}</span>
        <span>of {money(util.budget_amount)}</span>
        <span>· {util.utilization_percentage.toFixed(0)}% used</span>
        <span className={util.remaining_amount < 0 ? "font-medium text-error" : ""}>
          {util.remaining_amount >= 0
            ? `${money(util.remaining_amount)} left`
            : `${money(Math.abs(util.remaining_amount))} over`}
        </span>
      </div>
    </div>
  );
}

export default function BudgetsPage() {
  const toast = useToast();
  const list = useFetch(useCallback(() => budgetApi.list(), []), "budgets");

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Budget | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<Budget | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  async function saveBudget(values: BudgetFormValues) {
    setSaving(true);
    try {
      if (editing) {
        await budgetApi.update(editing.id, values);
        toast.success("Budget updated.");
      } else {
        await budgetApi.create(values);
        toast.success("Budget created.");
      }
      setFormOpen(false);
      setEditing(null);
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the budget.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    setDeleteLoading(true);
    try {
      await budgetApi.remove(deleting.id);
      toast.success("Budget deleted.");
      setDeleting(null);
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not delete the budget.");
    } finally {
      setDeleteLoading(false);
    }
  }

  const budgets = list.data ?? [];
  // At-limit budgets first, then by utilization share.
  const sorted = [...budgets].sort(
    (a, b) => b.utilization.utilization_percentage - a.utilization.utilization_percentage,
  );

  return (
    <>
      <PageHeader
        title="Budgets"
        description="Spending limits with automatic threshold alerts."
        action={
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" aria-hidden />
            New budget
          </Button>
        }
      />

      <Card>
        {list.loading ? (
          <ListSkeleton rows={4} />
        ) : list.error ? (
          <ErrorState message={list.error} onRetry={list.retry} />
        ) : sorted.length === 0 ? (
          <EmptyState
            title="No budgets yet"
            description="Set a spending limit for a category or overall, and get warned before you cross it."
            action={
              <Button size="sm" onClick={() => setFormOpen(true)}>
                <Plus className="h-4 w-4" aria-hidden />
                Create your first budget
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-border">
            {sorted.map((budget) => (
              <li key={budget.id} className="px-4 py-4">
                <UtilizationBar budget={budget} />
                <div className="mt-2 flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(budget);
                      setFormOpen(true);
                    }}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleting(budget)}
                    className="text-xs font-medium text-error hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Modal
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        title={editing ? "Edit budget" : "New budget"}
      >
        <BudgetForm
          initial={editing ?? undefined}
          submitting={saving}
          onSubmit={saveBudget}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
        />
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        loading={deleteLoading}
        title="Delete budget"
        message={
          deleting
            ? `Delete the ${deleting.category ?? "overall"} budget of ${money(deleting.amount)}? Related alerts are also removed.`
            : ""
        }
      />
    </>
  );
}

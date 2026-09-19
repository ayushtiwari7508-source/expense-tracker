"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import type { EChartsCoreOption } from "echarts";
import { ChartContainer, axisStyles, chartBase } from "@/components/ChartContainer";
import { PageHeader } from "@/components/PageHeader";
import { Stat } from "@/components/Stat";
import { Badge, Button, Card, CardHeader, Select } from "@/components/ui";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/states";
import { analyticsApi, budgetApi } from "@/lib/api";
import { money, moneyShort, pct, periodLabel, shortDate, todayISO } from "@/lib/format";
import { useFetch } from "@/lib/use-fetch";

const RANGES = [
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "365", label: "Last 12 months" },
] as const;

function rangeDates(days: number): { start: string; end: string } {
  const end = todayISO();
  const startDate = new Date(`${end}T00:00:00`);
  startDate.setDate(startDate.getDate() - (days - 1));
  const offsetMs = startDate.getTimezoneOffset() * 60_000;
  return { start: new Date(startDate.getTime() - offsetMs).toISOString().slice(0, 10), end };
}

export default function DashboardPage() {
  const [days, setDays] = useState<number>(30);
  const { start, end } = useMemo(() => rangeDates(days), [days]);
  const granularity = days > 120 ? "monthly" : "daily";

  // ---------------------------------------------------------------- data
  const summary = useFetch(
    useCallback(() => analyticsApi.summary(start, end), [start, end]),
    `summary:${start}:${end}`,
  );
  const series = useFetch(
    useCallback(() => analyticsApi.timeSeries(granularity, start, end, 7), [granularity, start, end]),
    `series:${granularity}:${start}:${end}`,
  );
  const categories = useFetch(
    useCallback(() => analyticsApi.categories(start, end), [start, end]),
    `categories:${start}:${end}`,
  );
  const budgets = useFetch(useCallback(() => budgetApi.list(), []), "budgets");
  const top = useFetch(
    useCallback(() => analyticsApi.topExpenses(5, start, end), [start, end]),
    `top:${start}:${end}`,
  );

  const chartOption = useMemo<EChartsCoreOption | null>(() => {
    const points = series.data?.points ?? [];
    if (points.length === 0) return null;
    return {
      ...chartBase,
      xAxis: {
        type: "category",
        data: points.map((point) => periodLabel(point.period)),
        ...axisStyles.categoryAxis,
      },
      yAxis: { type: "value", ...axisStyles.valueAxis },
      series: [
        {
          name: "Spending",
          type: "line",
          data: points.map((point) => point.total),
          showSymbol: false,
          lineStyle: { color: "#166534", width: 2 },
          areaStyle: { color: "rgba(22, 101, 52, 0.07)" },
        },
        {
          name: "7-period average",
          type: "line",
          data: points.map((point) => point.moving_average),
          showSymbol: false,
          lineStyle: { color: "#a8a29e", width: 1.5, type: "dashed" },
        },
      ],
      legend: { show: points.some((p) => p.moving_average !== null), textStyle: { color: "#78716c", fontSize: 11 } },
    } satisfies EChartsCoreOption;
  }, [series.data]);

  const categoryOption = useMemo<EChartsCoreOption | null>(() => {
    const rows = categories.data ?? [];
    if (rows.length === 0) return null;
    return {
      ...chartBase,
      xAxis: {
        type: "value",
        ...axisStyles.valueAxis,
        axisLabel: { ...axisStyles.valueAxis.axisLabel, formatter: (value: number) => moneyShort(value) },
      },
      yAxis: {
        type: "category",
        data: rows.map((row) => row.category).reverse(),
        ...axisStyles.categoryAxis,
      },
      series: [
        {
          type: "bar",
          data: rows.map((row) => row.total).reverse(),
          barMaxWidth: 18,
          itemStyle: { color: "#166534" },
          label: { show: true, position: "right", color: "#78716c", fontSize: 11, formatter: (p: { value: number }) => moneyShort(p.value) },
        },
      ],
    } satisfies EChartsCoreOption;
  }, [categories.data]);

  const activeBudgets = (budgets.data ?? []).filter(
    (budget) => budget.end_date >= start,
  );

  // ---------------------------------------------------------------- view
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Your spending at a glance."
        action={
          <Select
            aria-label="Date range"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="w-40"
          >
            {RANGES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        }
      />

      {/* Summary — four numbers that answer the core questions */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-6 border-y border-border py-6 lg:grid-cols-4">
        <Stat
          label="Total spent"
          value={money(summary.data?.total_amount ?? null)}
          hint={`${summary.data?.total_expenses ?? 0} expenses`}
        />
        <Stat
          label="Average expense"
          value={money(summary.data?.average_expense ?? null)}
        />
        <Stat
          label="Highest expense"
          value={money(summary.data?.highest_expense ?? null)}
        />
        <Stat
          label="vs previous period"
          value={summary.data?.percentage_change != null ? pct(summary.data.percentage_change) : "—"}
          delta={summary.data?.percentage_change ?? null}
          hint="spending change"
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        {/* Spending over time */}
        <Card className="lg:col-span-2">
          <CardHeader
            title={granularity === "daily" ? "Spending by day" : "Spending by month"}
            action={
              <Link href="/analytics" className="text-xs font-medium text-primary hover:underline">
                Full analytics
              </Link>
            }
          />
          {series.loading ? (
            <ListSkeleton rows={4} />
          ) : series.error ? (
            <ErrorState message={series.error} onRetry={series.retry} />
          ) : chartOption ? (
            <div className="p-2">
              <ChartContainer option={chartOption} ariaLabel="Spending over time" />
            </div>
          ) : (
            <EmptyState
              title="No expenses in this period"
              description="Record an expense to see your spending over time."
              action={
                <Link href="/expenses">
                  <Button size="sm">Add expense</Button>
                </Link>
              }
            />
          )}
        </Card>

        {/* Budget status */}
        <Card>
          <CardHeader
            title="Budgets"
            action={
              <Link href="/budgets" className="text-xs font-medium text-primary hover:underline">
                Manage
              </Link>
            }
          />
          {budgets.loading ? (
            <ListSkeleton rows={3} />
          ) : budgets.error ? (
            <ErrorState message={budgets.error} onRetry={budgets.retry} />
          ) : activeBudgets.length === 0 ? (
            <EmptyState
              title="No budgets yet"
              description="Set a limit to track your spending against it."
              action={
                <Link href="/budgets">
                  <Button size="sm" variant="secondary">
                    Create budget
                  </Button>
                </Link>
              }
            />
          ) : (
            <ul className="divide-y divide-border">
              {activeBudgets.slice(0, 4).map((budget) => {
                const util = budget.utilization;
                const tone =
                  util.status === "EXCEEDED" ? "error" : util.status === "WARNING" ? "warning" : "success";
                return (
                  <li key={budget.id} className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground">
                        {budget.category ?? "Overall"}
                      </span>
                      <Badge tone={tone}>{util.status}</Badge>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded bg-background">
                      <div
                        className={`h-full rounded ${
                          util.status === "EXCEEDED"
                            ? "bg-error"
                            : util.status === "WARNING"
                              ? "bg-warning"
                              : "bg-success"
                        }`}
                        style={{ width: `${Math.min(100, util.utilization_percentage)}%` }}
                      />
                    </div>
                    <p className="tnum mt-1.5 text-xs text-muted">
                      {money(util.amount_spent)} of {money(util.budget_amount)} ·{" "}
                      {util.utilization_percentage.toFixed(0)}%
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Category breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader title="Spending by category" />
          {categories.loading ? (
            <ListSkeleton rows={4} />
          ) : categories.error ? (
            <ErrorState message={categories.error} onRetry={categories.retry} />
          ) : categoryOption ? (
            <div className="p-2">
              <ChartContainer option={categoryOption} height={260} ariaLabel="Spending by category" />
            </div>
          ) : (
            <EmptyState title="Nothing to break down yet" description="Categories appear once you record expenses." />
          )}
        </Card>

        {/* Top expenses */}
        <Card>
          <CardHeader title="Largest expenses" />
          {top.loading ? (
            <ListSkeleton rows={4} />
          ) : top.error ? (
            <ErrorState message={top.error} onRetry={top.retry} />
          ) : (top.data ?? []).length === 0 ? (
            <EmptyState title="No expenses yet" description="Your largest expenses will show up here." />
          ) : (
            <ul className="divide-y divide-border">
              {(top.data ?? []).map((item) => (
                <li key={item.id} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {item.category}
                    </p>
                    <p className="text-xs text-muted">{shortDate(item.expense_date)}</p>
                  </div>
                  <p className="tnum text-sm font-medium text-foreground">{money(item.amount)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}

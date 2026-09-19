"use client";

import { useCallback, useMemo, useState } from "react";
import type { EChartsCoreOption } from "echarts";
import { ChartContainer, axisStyles, chartBase } from "@/components/ChartContainer";
import { PageHeader } from "@/components/PageHeader";
import { Stat } from "@/components/Stat";
import { Badge, Card, CardHeader, Select } from "@/components/ui";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/states";
import { analyticsApi } from "@/lib/api";
import { money, pct, periodLabel, shortDate, todayISO } from "@/lib/format";
import { useFetch } from "@/lib/use-fetch";

const GRANULARITIES = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
] as const;

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

export default function AnalyticsPage() {
  const [days, setDays] = useState(90);
  const [granularity, setGranularity] = useState<string>("weekly");
  const { start, end } = useMemo(() => rangeDates(days), [days]);
  const rangeKey = `${start}:${end}`;

  const summary = useFetch(
    useCallback(() => analyticsApi.summary(start, end), [start, end]),
    `summary:${rangeKey}`,
  );
  const series = useFetch(
    useCallback(() => analyticsApi.timeSeries(granularity, start, end, 4), [granularity, start, end]),
    `series:${granularity}:${rangeKey}`,
  );
  const categories = useFetch(
    useCallback(() => analyticsApi.categories(start, end), [start, end]),
    `categories:${rangeKey}`,
  );
  const top = useFetch(
    useCallback(() => analyticsApi.topExpenses(10, start, end), [start, end]),
    `top:${rangeKey}`,
  );
  const insights = useFetch(
    useCallback(() => analyticsApi.insights(start, end), [start, end]),
    `insights:${rangeKey}`,
  );

  const trendOption = useMemo<EChartsCoreOption | null>(() => {
    const points = series.data?.points ?? [];
    if (points.length === 0) return null;
    return {
      ...chartBase,
      legend: { show: true, textStyle: { color: "#78716c", fontSize: 11 } },
      xAxis: {
        type: "category",
        data: points.map((point) => periodLabel(point.period)),
        ...axisStyles.categoryAxis,
      },
      yAxis: { type: "value", ...axisStyles.valueAxis },
      series: [
        {
          name: "Spending",
          type: "bar",
          data: points.map((point) => point.total),
          barMaxWidth: 26,
          itemStyle: { color: "#166534" },
        },
        {
          name: "Moving average",
          type: "line",
          data: points.map((point) => point.moving_average),
          showSymbol: false,
          lineStyle: { color: "#b45309", width: 2 },
        },
      ],
    } satisfies EChartsCoreOption;
  }, [series.data]);

  const shareOption = useMemo<EChartsCoreOption | null>(() => {
    const rows = categories.data ?? [];
    if (rows.length === 0) return null;
    return {
      ...chartBase,
      tooltip: { ...chartBase.tooltip, trigger: "item" as const },
      legend: { orient: "vertical" as const, right: 8, top: "middle", textStyle: { color: "#78716c", fontSize: 11 } },
      series: [
        {
          type: "pie",
          radius: ["45%", "70%"],
          center: ["35%", "50%"],
          data: rows.map((row) => ({ name: row.category, value: row.total })),
          label: { show: false },
          itemStyle: { borderColor: "#ffffff", borderWidth: 1 },
          color: ["#166534", "#3f6212", "#4d7c0f", "#15803d", "#065f46", "#a16207", "#92400e", "#57534e", "#78716c"],
        },
      ],
    } satisfies EChartsCoreOption;
  }, [categories.data]);

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Where your money goes, and how it changes."
        action={
          <div className="flex items-center gap-2">
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
          </div>
        }
      />

      {/* Headline numbers */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-6 border-y border-border py-6 lg:grid-cols-4">
        <Stat label="Total spent" value={money(summary.data?.total_amount ?? null)} />
        <Stat label="Average expense" value={money(summary.data?.average_expense ?? null)} />
        <Stat label="Highest expense" value={money(summary.data?.highest_expense ?? null)} />
        <Stat
          label="vs previous period"
          value={summary.data?.percentage_change != null ? pct(summary.data.percentage_change) : "—"}
          delta={summary.data?.percentage_change ?? null}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        {/* Trend chart with granularity switch */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Spending trend"
            action={
              <div className="flex gap-1">
                {GRANULARITIES.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setGranularity(option.value)}
                    className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                      granularity === option.value
                        ? "bg-primary/10 text-primary"
                        : "text-muted hover:bg-background hover:text-foreground"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            }
          />
          {series.loading ? (
            <ListSkeleton rows={4} />
          ) : series.error ? (
            <ErrorState message={series.error} onRetry={series.retry} />
          ) : trendOption ? (
            <div className="p-2">
              <ChartContainer option={trendOption} height={300} ariaLabel="Spending trend" />
            </div>
          ) : (
            <EmptyState title="No data in this period" description="Record expenses to see trends." />
          )}
          {series.data && series.data.points.length > 1 && (
            <p className="border-t border-border px-4 py-2.5 text-xs text-muted">
              Trend: <span className="font-medium text-foreground">{series.data.trend_direction}</span>
              {series.data.percentage_change != null && (
                <> · {pct(series.data.percentage_change)} from first to last period</>
              )}
            </p>
          )}
        </Card>

        {/* Category share */}
        <Card>
          <CardHeader title="Category share" />
          {categories.loading ? (
            <ListSkeleton rows={4} />
          ) : categories.error ? (
            <ErrorState message={categories.error} onRetry={categories.retry} />
          ) : shareOption ? (
            <div className="p-2">
              <ChartContainer option={shareOption} height={300} ariaLabel="Spending share by category" />
            </div>
          ) : (
            <EmptyState title="No data in this period" />
          )}
        </Card>

        {/* Factual insights */}
        <Card className="lg:col-span-2">
          <CardHeader title="Insights" />
          {insights.loading ? (
            <ListSkeleton rows={3} />
          ) : insights.error ? (
            <ErrorState message={insights.error} onRetry={insights.retry} />
          ) : (insights.data?.insights ?? []).length === 0 ? (
            <EmptyState
              title="Not enough data yet"
              description="Insights appear once you have expenses in this period."
            />
          ) : (
            <ul className="divide-y divide-border">
              {(insights.data?.insights ?? []).map((insight, index) => (
                <li key={index} className="flex items-start gap-3 px-4 py-3">
                  <Badge tone="neutral">{insight.type.replace("_", " ")}</Badge>
                  <p className="text-sm text-foreground">{insight.message}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Top expenses */}
        <Card>
          <CardHeader title="Largest expenses" />
          {top.loading ? (
            <ListSkeleton rows={5} />
          ) : top.error ? (
            <ErrorState message={top.error} onRetry={top.retry} />
          ) : (top.data ?? []).length === 0 ? (
            <EmptyState title="No expenses in this period" />
          ) : (
            <ol className="divide-y divide-border">
              {(top.data ?? []).map((item) => (
                <li key={item.id} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      <span className="tnum mr-2 text-muted">#{item.rank}</span>
                      {item.category}
                    </p>
                    <p className="text-xs text-muted">{shortDate(item.expense_date)}</p>
                  </div>
                  <p className="tnum text-sm font-medium text-foreground">{money(item.amount)}</p>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </>
  );
}

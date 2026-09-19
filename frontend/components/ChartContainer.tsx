"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

// Thin ECharts wrapper: owns init, updates, resize, and disposal.
export function ChartContainer({
  option,
  height = 280,
  ariaLabel,
}: {
  option: echarts.EChartsCoreOption;
  height?: number;
  ariaLabel: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current);
    chartRef.current = chart;

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      role="img"
      aria-label={ariaLabel}
      className="w-full"
    />
  );
}

// Shared axis/text styling so every chart reads the same.
export const chartBase = {
  textStyle: { color: "#78716c", fontSize: 12 },
  grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
  tooltip: {
    trigger: "axis" as const,
    backgroundColor: "#ffffff",
    borderColor: "#e5e5e2",
    textStyle: { color: "#1c1917", fontSize: 12 },
  },
};

export const axisStyles = {
  categoryAxis: {
    axisLine: { lineStyle: { color: "#e5e5e2" } },
    axisTick: { show: false },
    axisLabel: { color: "#78716c", fontSize: 11 },
  },
  valueAxis: {
    splitLine: { lineStyle: { color: "#f0f0ee" } },
    axisLabel: { color: "#78716c", fontSize: 11 },
  },
};

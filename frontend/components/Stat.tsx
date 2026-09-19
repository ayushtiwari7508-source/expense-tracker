"use client";

import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

export function Stat({
  label,
  value,
  hint,
  delta,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  delta?: number | null;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className="tnum text-2xl font-semibold text-foreground">{value}</p>
      {(hint || delta !== undefined) && (
        <div className="flex items-center gap-2 text-xs text-muted">
          {typeof delta === "number" && (
            <span
              className={`tnum inline-flex items-center gap-0.5 font-medium ${
                delta > 0 ? "text-warning" : delta < 0 ? "text-success" : "text-muted"
              }`}
            >
              {delta > 0 ? (
                <ArrowUpRight className="h-3 w-3" aria-hidden />
              ) : delta < 0 ? (
                <ArrowDownRight className="h-3 w-3" aria-hidden />
              ) : null}
              {Math.abs(delta).toFixed(1)}%
            </span>
          )}
          {hint && <span>{hint}</span>}
        </div>
      )}
    </div>
  );
}

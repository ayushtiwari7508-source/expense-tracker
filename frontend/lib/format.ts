// Formatting helpers. Intl does the locale work; no floats in logic.

export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

export function moneyShort(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export function mediumDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

// "2026-09" → "Sep 2026"; "2026-W37" → "W37 2026"; dates pass through.
export function periodLabel(period: string): string {
  const monthly = /^(\d{4})-(\d{2})$/.exec(period);
  if (monthly) {
    return new Date(Number(monthly[1]), Number(monthly[2]) - 1, 1).toLocaleDateString("en-IN", {
      month: "short",
      year: "numeric",
    });
  }
  const weekly = /^(\d{4})-W(\d{2})$/.exec(period);
  if (weekly) return `W${weekly[2]} ${weekly[1]}`;
  return period;
}

export function todayISO(): string {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

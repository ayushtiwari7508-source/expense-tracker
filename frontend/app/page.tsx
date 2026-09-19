"use client";

import Link from "next/link";
import { ArrowRight, Bell, ChartLine, Receipt, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const STEPS = [
  {
    icon: Receipt,
    title: "Record expenses",
    description: "Log what you spend with category, payment method, and date.",
  },
  {
    icon: Wallet,
    title: "Set budgets",
    description: "Monthly limits overall or per category, with warning thresholds.",
  },
  {
    icon: Bell,
    title: "Get alerted",
    description: "Know when a budget crosses its threshold or is exceeded.",
  },
  {
    icon: ChartLine,
    title: "Review trends",
    description: "Daily and monthly totals, top expenses, and category breakdowns.",
  },
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const dashboardHref = user ? "/dashboard" : "/login";

  return (
    <div className="mx-auto flex min-h-screen max-w-page flex-col px-4 md:px-8">
      <header className="flex items-center justify-between py-5">
        <div className="flex items-center gap-2">
          <Wallet className="h-5 w-5 text-primary" aria-hidden />
          <span className="text-sm font-semibold tracking-tight text-foreground">
            Expense Tracker
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!loading && !user && (
            <Link
              href="/login"
              className="rounded px-3 py-1.5 text-sm font-medium text-muted hover:text-foreground"
            >
              Sign in
            </Link>
          )}
          <Link
            href={dashboardHref}
            className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover"
          >
            {user ? "Open app" : "Get started"}
          </Link>
        </div>
      </header>

      <main className="flex flex-1 flex-col justify-center py-12">
        {/* What it does — plain statement, no hero theatrics */}
        <h1 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
          Track expenses and compare monthly spending.
        </h1>
        <p className="mt-3 max-w-xl text-base text-muted">
          A straightforward ledger for your money: record expenses, set budget
          limits, and see where your money goes each month.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href={dashboardHref}
            className="inline-flex h-10 items-center gap-2 rounded bg-primary px-5 text-sm font-medium text-white hover:bg-primary-hover"
          >
            {user ? "Go to dashboard" : "Create an account"}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link
            href="/login"
            className="inline-flex h-10 items-center rounded border border-border bg-surface px-5 text-sm font-medium text-foreground hover:bg-background"
          >
            Sign in
          </Link>
        </div>

        {/* How the workflow works */}
        <ol className="mt-14 grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="border-t border-border pt-4">
              <div className="flex items-center gap-2 text-muted">
                <step.icon className="h-4 w-4" aria-hidden />
                <span className="tnum text-xs font-medium">Step {index + 1}</span>
              </div>
              <h2 className="mt-2 text-sm font-semibold text-foreground">{step.title}</h2>
              <p className="mt-1 text-sm text-muted">{step.description}</p>
            </li>
          ))}
        </ol>
      </main>

      <footer className="border-t border-border py-5">
        <p className="text-xs text-muted">
          Works with the Expense Tracker API — your data stays in your own database.
        </p>
      </footer>
    </div>
  );
}

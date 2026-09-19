"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import {
  Bell,
  ChartLine,
  LayoutDashboard,
  LogOut,
  Receipt,
  Settings,
  Wallet,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { PageLoading } from "./states";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/expenses", label: "Expenses", icon: Receipt },
  { href: "/budgets", label: "Budgets", icon: Wallet },
  { href: "/analytics", label: "Analytics", icon: ChartLine },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

function NavLink({ href, label, icon: Icon, active }: {
  href: string;
  label: string;
  icon: typeof Receipt;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 rounded px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? "bg-primary/10 text-primary"
          : "text-muted hover:bg-background hover:text-foreground"
      }`}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {label}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) return <PageLoading label="Checking session" />;
  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-surface md:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <Wallet className="h-5 w-5 text-primary" aria-hidden />
          <span className="text-sm font-semibold tracking-tight text-foreground">
            Expense Tracker
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname.startsWith(item.href)}
            />
          ))}
        </nav>
        <div className="border-t border-border px-4 py-4">
          <Link href="/settings" className="block">
            <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
          </Link>
          <div className="mt-3 flex items-center gap-4">
            <Link
              href="/settings"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-foreground"
            >
              <Settings className="h-3.5 w-3.5" aria-hidden />
              Settings
            </Link>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-foreground"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
          <div className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-primary" aria-hidden />
            <span className="text-sm font-semibold tracking-tight">Expense Tracker</span>
          </div>
          <button
            type="button"
            onClick={logout}
            className="text-muted hover:text-foreground"
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" aria-hidden />
          </button>
        </header>

        <main className="mx-auto w-full max-w-page flex-1 px-4 py-6 pb-24 md:px-8 md:pb-10">
          {children}
        </main>

        {/* Mobile bottom navigation */}
        <nav
          className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface md:hidden"
          aria-label="Primary mobile"
        >
          {NAV_ITEMS.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs font-medium ${
                  active ? "text-primary" : "text-muted"
                }`}
              >
                <item.icon className="h-4 w-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

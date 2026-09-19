"use client";

import type { ReactNode } from "react";
import { AlertTriangle, Inbox } from "lucide-react";
import { Button, Spinner } from "./ui";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <Inbox className="h-6 w-6 text-subtle" aria-hidden />
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && <p className="max-w-sm text-sm text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <AlertTriangle className="h-6 w-6 text-error" aria-hidden />
      <p className="text-sm font-medium text-foreground">Something went wrong</p>
      <p className="max-w-sm text-sm text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-2">
          Try again
        </Button>
      )}
    </div>
  );
}

// Skeleton rows for tables/lists; keeps layout stable while loading.
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-border" role="status" aria-label="Loading items">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center justify-between px-4 py-3.5" aria-hidden>
          <div className="h-3.5 w-40 animate-pulse rounded bg-background" />
          <div className="h-3.5 w-20 animate-pulse rounded bg-background" />
        </div>
      ))}
    </div>
  );
}

export function PageLoading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Spinner label={label} />
    </div>
  );
}

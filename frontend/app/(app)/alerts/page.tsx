"use client";

import { useCallback, useState } from "react";
import { BellOff, CheckCheck } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, Button, Card } from "@/components/ui";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/states";
import { alertApi } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useToast } from "@/lib/toast-context";
import { useFetch } from "@/lib/use-fetch";

export default function AlertsPage() {
  const toast = useToast();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const list = useFetch(
    useCallback(() => alertApi.list(unreadOnly), [unreadOnly]),
    `alerts:${unreadOnly}`,
  );
  const [markingAll, setMarkingAll] = useState(false);

  async function markRead(id: string) {
    try {
      await alertApi.markRead(id);
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the alert.");
    }
  }

  async function markAllRead() {
    setMarkingAll(true);
    try {
      await alertApi.markAllRead();
      toast.success("All alerts marked as read.");
      list.retry();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update alerts.");
    } finally {
      setMarkingAll(false);
    }
  }

  const items = list.data?.items ?? [];
  const unreadCount = list.data?.unread_count ?? 0;

  return (
    <>
      <PageHeader
        title="Alerts"
        description={
          unreadCount > 0 ? `${unreadCount} unread alert${unreadCount === 1 ? "" : "s"}` : "You're all caught up."
        }
        action={
          <div className="flex items-center gap-2">
            <Button
              variant={unreadOnly ? "primary" : "secondary"}
              size="sm"
              onClick={() => setUnreadOnly((current) => !current)}
            >
              Unread only
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={markAllRead}
              loading={markingAll}
              disabled={unreadCount === 0}
            >
              <CheckCheck className="h-4 w-4" aria-hidden />
              Mark all read
            </Button>
          </div>
        }
      />

      <Card>
        {list.loading ? (
          <ListSkeleton rows={5} />
        ) : list.error ? (
          <ErrorState message={list.error} onRetry={list.retry} />
        ) : items.length === 0 ? (
          <EmptyState
            title={unreadOnly ? "No unread alerts" : "No alerts yet"}
            description={
              unreadOnly
                ? "Everything has been read."
                : "Alerts appear when a budget crosses its warning threshold or is exceeded."
            }
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((alert) => (
              <li
                key={alert.id}
                className={`flex items-start gap-3 px-4 py-3.5 ${alert.is_read ? "" : "bg-primary/[0.03]"}`}
              >
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                    alert.is_read ? "bg-transparent" : alert.type === "exceeded" ? "bg-error" : "bg-warning"
                  }`}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={alert.type === "exceeded" ? "error" : "warning"}>
                      {alert.type === "exceeded" ? "Budget exceeded" : "Budget warning"}
                    </Badge>
                    {!alert.is_read && <span className="text-xs font-medium text-foreground">Unread</span>}
                    <span className="text-xs text-muted">{dateTime(alert.created_at)}</span>
                  </div>
                  <p className={`mt-1 text-sm ${alert.is_read ? "text-muted" : "font-medium text-foreground"}`}>
                    {alert.message}
                  </p>
                </div>
                {!alert.is_read && (
                  <button
                    type="button"
                    onClick={() => markRead(alert.id)}
                    className="shrink-0 text-xs font-medium text-primary hover:underline"
                  >
                    Mark read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {items.length === 0 && !list.loading && !list.error && (
        <div className="mt-4 flex items-center gap-2 text-xs text-muted">
          <BellOff className="h-3.5 w-3.5" aria-hidden />
          Budget alerts are checked whenever you view a budget.
        </div>
      )}
    </>
  );
}

"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

// Returns currently focusable elements inside the modal panel.
function focusableElements(panel: HTMLElement): HTMLElement[] {
  return Array.from(
    panel.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => element.offsetParent !== null || element === document.activeElement);
}

export function Modal({ open, onClose, title, children }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    // Remember where focus came from so it can be restored on close.
    restoreFocusRef.current = document.activeElement as HTMLElement | null;

    const panel = panelRef.current;
    if (panel) {
      panel.focus();
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;

      // Trap Tab within the dialog panel.
      const elements = focusableElements(panelRef.current);
      if (elements.length === 0) return;
      const first = elements[0];
      const last = elements[elements.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && (active === first || active === panelRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
      // Return focus to the element that opened the dialog.
      restoreFocusRef.current?.focus?.();
      restoreFocusRef.current = null;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-end justify-center bg-foreground/40 p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="max-h-[92vh] w-full overflow-y-auto rounded-t-lg border border-border bg-surface shadow-overlay outline-none sm:max-w-lg sm:rounded-lg"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted hover:bg-background hover:text-foreground"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Delete",
  loading = false,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-muted">{message}</p>
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="h-9 rounded border border-border bg-surface px-4 text-sm font-medium text-foreground hover:bg-background"
          disabled={loading}
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="h-9 rounded bg-error px-4 text-sm font-medium text-white hover:bg-error/90 disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Deleting…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

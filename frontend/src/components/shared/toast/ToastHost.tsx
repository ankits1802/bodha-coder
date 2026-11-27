"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { useShortcuts } from "../shortcuts/useShortcuts";
import { SHARED_TEXT } from "../strings";
import { dismissToast, runToastAction, TOAST_SECONDS, useToast } from "./toastStore";

export function ToastHost() {
  const toast = useToast();
  const words = SHARED_TEXT.toast;
  useShortcuts("global", { undo: toast?.action ? () => void runToastAction() : undefined });

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => dismissToast(toast.id), TOAST_SECONDS * 1000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  return (
    <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-24 z-40 flex justify-center px-4">
      {toast ? (
        <div className="pointer-events-auto flex items-center gap-3 rounded-full bg-surface py-1.5 pr-1.5 pl-5 shadow-float">
          <span className="text-body text-label">{toast.message}</span>
          {toast.action ? (
            <Button size="sm" onClick={() => void runToastAction()}>
              {toast.action.label}
            </Button>
          ) : null}
          <Button size="sm" variant="plain" aria-label={words.dismiss} onClick={() => dismissToast(toast.id)}>
            ×
          </Button>
        </div>
      ) : null}
    </div>
  );
}

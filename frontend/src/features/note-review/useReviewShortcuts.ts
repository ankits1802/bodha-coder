"use client";

import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";

export type ShortcutKey = "j" | "k" | "a" | "p";
export type ShortcutHandlers = Partial<Record<ShortcutKey, () => void>>;

export function useReviewShortcuts(handlers: ShortcutHandlers): void {
  useShortcuts("review", {
    nextNote: handlers.j,
    previousNote: handlers.k,
    approve: handlers.a,
    askProvider: handlers.p,
  });
}

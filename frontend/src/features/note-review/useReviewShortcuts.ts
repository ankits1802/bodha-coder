"use client";

import { useShortcuts, type ShortcutHandlers } from "@/components/shared/shortcuts/useShortcuts";

export type ReviewShortcutHandlers = Pick<ShortcutHandlers, "nextNote" | "previousNote" | "approve" | "askProvider">;

export function useReviewShortcuts(handlers: ReviewShortcutHandlers): void {
  useShortcuts("review", handlers);
}

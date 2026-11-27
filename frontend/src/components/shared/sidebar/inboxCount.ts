"use client";

import { useEffect, useSyncExternalStore } from "react";
import { getInboxCount } from "@/lib/api/inbox";

export const INBOX_POLL_MS = 120_000;

let unread: number | null = null;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function announceInboxCount(count: number): void {
  unread = count;
  for (const listener of listeners) listener();
}

export function useInboxCount(enabled: boolean, pathname: string): number | undefined {
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    const load = () => {
      if (document.hidden) return;
      getInboxCount().then(
        (count) => {
          if (live) announceInboxCount(count.unread);
        },
        () => undefined,
      );
    };
    load();
    const timer = window.setInterval(load, INBOX_POLL_MS);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [enabled, pathname]);
  const current = useSyncExternalStore(
    subscribe,
    () => unread,
    () => null,
  );
  return enabled && current !== null ? current : undefined;
}

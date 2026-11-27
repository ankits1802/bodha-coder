"use client";

import { useSyncExternalStore } from "react";

export type Overlay = "search" | "shortcuts";

let current: Overlay | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function openOverlay(overlay: Overlay): void {
  current = overlay;
  emit();
}

export function closeOverlay(): void {
  current = null;
  emit();
}

export function useOpenOverlay(): Overlay | null {
  return useSyncExternalStore(
    subscribe,
    () => current,
    () => null,
  );
}

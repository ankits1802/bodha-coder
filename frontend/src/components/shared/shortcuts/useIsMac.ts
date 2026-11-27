"use client";

import { useSyncExternalStore } from "react";

const APPLE_PLATFORM = /Mac|iPhone|iPad/;

function noChange(): () => void {
  return () => undefined;
}

export function useIsMac(): boolean {
  return useSyncExternalStore(
    noChange,
    () => APPLE_PLATFORM.test(navigator.userAgent),
    () => false,
  );
}

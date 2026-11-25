"use client";

import { useEffect, useSyncExternalStore } from "react";

interface Captured {
  path: string;
  token: string | null;
}

let captured: Captured | null = null;

function decoded(raw: string): string | null {
  try {
    return decodeURIComponent(raw);
  } catch {
    return null;
  }
}

function readFragmentToken(): string | null {
  const path = window.location.pathname;
  if (captured?.path !== path) {
    const raw = window.location.hash.slice(1);
    captured = { path, token: raw ? decoded(raw) : null };
  }
  return captured.token;
}

function subscribe(): () => void {
  return () => undefined;
}

function serverToken(): undefined {
  return undefined;
}

export function useFragmentToken(): string | null | undefined {
  const token = useSyncExternalStore(subscribe, readFragmentToken, serverToken);

  useEffect(() => {
    if (!window.location.hash) return;
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}`);
  }, [token]);

  return token;
}

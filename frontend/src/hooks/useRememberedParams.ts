"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { useSession } from "@/lib/session/useSession";

export function rememberedParams(search: URLSearchParams, keys: readonly string[]): string {
  const kept = new URLSearchParams();
  for (const key of keys) {
    const value = search.get(key);
    if (value) kept.set(key, value);
  }
  return kept.toString();
}

function readSaved(storageKey: string): string | null {
  try {
    return window.localStorage.getItem(storageKey);
  } catch {
    return null;
  }
}

function save(storageKey: string, value: string): void {
  try {
    window.localStorage.setItem(storageKey, value);
  } catch {
    return;
  }
}

export function useRememberedParams(screen: string, keys: readonly string[]): void {
  const { user } = useSession();
  const search = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const restored = useRef(false);
  const storageKey = user ? `bodha.${screen}.${user.id}` : null;
  const current = rememberedParams(search, keys);
  const untouched = search.toString() === "";

  useEffect(() => {
    if (storageKey === null) return;
    if (!restored.current) {
      restored.current = true;
      const saved = readSaved(storageKey);
      if (untouched && saved) {
        router.replace(`${pathname}?${saved}`, { scroll: false });
        return;
      }
    }
    save(storageKey, current);
  }, [storageKey, current, untouched, pathname, router]);
}

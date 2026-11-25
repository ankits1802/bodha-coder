"use client";

import { useState } from "react";
import { messageOf } from "@/lib/api/errors";

export type Outcome<R> = { ok: true; value: R } | { ok: false; error: string };

export interface Action<A extends unknown[], R> {
  run: (...args: A) => Promise<Outcome<R>>;
  pending: boolean;
  error: string | null;
  clearError: () => void;
}

export function useAction<A extends unknown[], R>(action: (...args: A) => Promise<R>): Action<A, R> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(...args: A): Promise<Outcome<R>> {
    setPending(true);
    setError(null);
    try {
      return { ok: true, value: await action(...args) };
    } catch (caught) {
      const message = messageOf(caught);
      setError(message);
      return { ok: false, error: message };
    } finally {
      setPending(false);
    }
  }

  return { run, pending, error, clearError: () => setError(null) };
}

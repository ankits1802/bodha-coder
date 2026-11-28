"use client";

import { useState } from "react";

export type CopyState = "idle" | "copied" | "failed";

export interface Copier {
  state: CopyState;
  copy: (text: string) => Promise<void>;
  reset: () => void;
}

export function useCopy(): Copier {
  const [state, setState] = useState<CopyState>("idle");

  async function copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
  }

  return { state, copy, reset: () => setState("idle") };
}

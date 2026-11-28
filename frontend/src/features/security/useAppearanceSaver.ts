"use client";

import { useRef, useState } from "react";
import { saveAppearance } from "@/lib/api/account";
import { messageOf } from "@/lib/api/errors";
import type { Appearance } from "@/lib/api/types";

export interface AppearanceSaver {
  save: (appearance: Appearance) => void;
  error: string | null;
}

export function useAppearanceSaver(): AppearanceSaver {
  const wanted = useRef<Appearance | null>(null);
  const running = useRef(false);
  const [error, setError] = useState<string | null>(null);

  async function flush(): Promise<void> {
    running.current = true;
    for (let next = wanted.current; next !== null; next = wanted.current) {
      wanted.current = null;
      try {
        await saveAppearance(next);
        setError(null);
      } catch (caught) {
        setError(messageOf(caught));
      }
    }
    running.current = false;
  }

  function save(appearance: Appearance): void {
    wanted.current = appearance;
    if (!running.current) void flush();
  }

  return { save, error };
}

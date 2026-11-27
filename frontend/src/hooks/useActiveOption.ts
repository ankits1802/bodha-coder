"use client";

import { useState, type KeyboardEvent } from "react";

const STEPS: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };

export interface ActiveOption {
  current: number;
  setActive: (index: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
}

export function optionId(listId: string, index: number): string {
  return `${listId}-option-${index}`;
}

export function useActiveOption<T>(items: readonly T[], onChoose: (item: T) => void): ActiveOption {
  const [active, setActive] = useState(0);
  const current = Math.max(0, Math.min(active, items.length - 1));

  function onKeyDown(event: KeyboardEvent<HTMLElement>): void {
    const step = STEPS[event.key];
    if (step !== undefined && items.length > 0) {
      event.preventDefault();
      setActive((current + step + items.length) % items.length);
      return;
    }
    const chosen = items[current];
    if (event.key === "Enter" && chosen !== undefined) {
      event.preventDefault();
      onChoose(chosen);
    }
  }

  return { current, setActive, onKeyDown };
}

"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { haptic } from "@/lib/haptics";
import { nextTabIndex } from "./tabKeys";

export interface RovingTabs {
  selected: number;
  choose: (index: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>, index: number) => void;
  refAt: (index: number) => (node: HTMLButtonElement | null) => void;
}

export function useRovingTabs(count: number): RovingTabs {
  const [selected, setSelected] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function choose(index: number): void {
    if (index !== selected) haptic("select");
    setSelected(index);
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const next = nextTabIndex(event.key, index, count);
    if (next === null) return;
    event.preventDefault();
    choose(next);
    refs.current[next]?.focus();
  }

  function refAt(index: number) {
    return (node: HTMLButtonElement | null) => {
      refs.current[index] = node;
    };
  }

  return { selected, choose, onKeyDown, refAt };
}

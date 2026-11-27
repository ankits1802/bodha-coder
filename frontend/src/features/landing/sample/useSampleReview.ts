"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { comboFor, type ShortcutId } from "@/components/shared/shortcuts/registry";
import { haptic } from "@/lib/haptics";
import { nextOpen, type Decision, type Decisions } from "./claim";
import type { SampleNote } from "./samples";

const KEYED: Partial<Record<ShortcutId, Decision>> = { acceptFinding: "accept", rejectFinding: "reject" };

export interface SampleReview {
  decisions: Decisions;
  current: string | null;
  point: (key: string) => void;
  choose: (key: string, decision: Decision) => void;
  onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
  refAt: (key: string) => (node: HTMLButtonElement | null) => void;
}

function withDecision(decisions: Decisions, key: string, decision: Decision | null): Decisions {
  const rest = Object.fromEntries(Object.entries(decisions).filter(([existing]) => existing !== key));
  return decision ? { ...rest, [key]: decision } : rest;
}

export function useSampleReview(sample: SampleNote): SampleReview {
  const [decisions, setDecisions] = useState<Decisions>({});
  const [current, setCurrent] = useState<string | null>(sample.findings[0]?.key ?? null);
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});

  function settle(key: string, decision: Decision | null): void {
    const next = withDecision(decisions, key, decision);
    setDecisions(next);
    if (decision === null) {
      setCurrent(key);
      haptic("select");
      return;
    }
    const following = nextOpen(sample.findings, next, key);
    setCurrent(following);
    haptic(following === null ? "success" : "select");
    if (following !== null) buttons.current[following]?.focus();
  }

  function choose(key: string, decision: Decision): void {
    settle(key, decisions[key] === decision ? null : decision);
  }

  function onKeyDown(event: KeyboardEvent<HTMLElement>): void {
    if (event.repeat || event.defaultPrevented) return;
    const found = comboFor(event, "review");
    const decision = found ? KEYED[found.shortcut.id] : undefined;
    if (!decision) return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-finding]");
    const key = row?.dataset.finding ?? current;
    if (!key) return;
    event.preventDefault();
    settle(key, decision);
  }

  function refAt(key: string) {
    return (node: HTMLButtonElement | null) => {
      buttons.current[key] = node;
    };
  }

  return { decisions, current, point: setCurrent, choose, onKeyDown, refAt };
}

"use client";

import { useState } from "react";
import { nextInOrder } from "./decisionFlow";

export const APPROVE_TARGET = "review-approve";

export interface FindingFocus {
  currentKey: string | null;
  moveAfter: (key: string) => void;
}

interface Position {
  tab: string;
  key: string | null;
}

function focusTarget(key: string | null): void {
  const selector =
    key === null ? `[data-target="${APPROVE_TARGET}"]` : `[data-finding-key="${CSS.escape(key)}"] [role="radio"][aria-checked="true"]`;
  const element = document.querySelector<HTMLElement>(selector);
  if (!element) return;
  element.focus({ preventScroll: true });
  element.scrollIntoView({ block: "nearest" });
}

export function currentFindingKey(order: string[], tab: string, position: Position | null): string | null {
  if (position === null || position.tab !== tab) return order[0] ?? null;
  if (position.key === null) return null;
  return order.includes(position.key) ? position.key : (order[0] ?? null);
}

export function useFindingFocus(order: string[], tab: string): FindingFocus {
  const [position, setPosition] = useState<Position | null>(null);

  function moveAfter(key: string): void {
    const next = nextInOrder(order, key);
    setPosition({ tab, key: next });
    window.requestAnimationFrame(() => focusTarget(next));
  }

  return { currentKey: currentFindingKey(order, tab, position), moveAfter };
}

"use client";

import { useState } from "react";
import { nextInOrder, stepInOrder } from "./decisionFlow";

export const APPROVE_TARGET = "review-approve";
export const FINDING_KEY_ATTRIBUTE = "data-finding-key";

export interface FindingFocus {
  currentKey: string | null;
  moveAfter: (key: string) => void;
  step: (direction: 1 | -1) => void;
  focusIn: (key: string) => void;
}

interface Position {
  key: string | null;
}

function focusTarget(key: string | null): void {
  const row = key === null ? null : `[${FINDING_KEY_ATTRIBUTE}="${CSS.escape(key)}"]`;
  const selector = row === null ? `[data-target="${APPROVE_TARGET}"]` : `${row} [role="radio"][tabindex="0"]`;
  const element = document.querySelector<HTMLElement>(selector);
  if (!element) return;
  element.focus({ preventScroll: true });
  element.scrollIntoView({ block: "nearest" });
}

export function currentFindingKey(order: string[], position: Position | null): string | null {
  if (position === null) return order[0] ?? null;
  if (position.key === null) return null;
  return order.includes(position.key) ? position.key : (order[0] ?? null);
}

export function useFindingFocus(order: string[]): FindingFocus {
  const [position, setPosition] = useState<Position | null>(null);
  const currentKey = currentFindingKey(order, position);

  function moveTo(key: string | null): void {
    setPosition({ key });
    window.requestAnimationFrame(() => focusTarget(key));
  }

  return {
    currentKey,
    moveAfter: (key) => moveTo(nextInOrder(order, key)),
    step: (direction) => moveTo(stepInOrder(order, currentKey, direction)),
    focusIn: (key) => {
      if (order.includes(key) && key !== currentKey) setPosition({ key });
    },
  };
}

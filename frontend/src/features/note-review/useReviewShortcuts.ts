"use client";

import { useEffect, useEffectEvent } from "react";

export type ShortcutKey = "j" | "k" | "a" | "p";
export type ShortcutHandlers = Partial<Record<ShortcutKey, () => void>>;

const TYPING_TAGS = ["INPUT", "TEXTAREA", "SELECT"];

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return TYPING_TAGS.includes(target.tagName) || target.isContentEditable;
}

function isShortcutKey(key: string): key is ShortcutKey {
  return key === "j" || key === "k" || key === "a" || key === "p";
}

export function useReviewShortcuts(handlers: ShortcutHandlers): void {
  const handle = useEffectEvent((event: KeyboardEvent) => {
    if (event.metaKey || event.ctrlKey || event.altKey || event.repeat) return;
    if (isTyping(event.target) || document.querySelector("dialog[open]")) return;
    const key = event.key.toLowerCase();
    if (!isShortcutKey(key)) return;
    const action = handlers[key];
    if (!action) return;
    event.preventDefault();
    action();
  });

  useEffect(() => {
    const listener = (event: KeyboardEvent) => handle(event);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
}

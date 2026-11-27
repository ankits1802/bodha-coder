"use client";

import { useEffect, useEffectEvent } from "react";
import { comboFor, isTyping, type ShortcutId, type ShortcutScope } from "./registry";

export type ShortcutHandlers = Partial<Record<ShortcutId, () => void>>;

export function useShortcuts(scope: ShortcutScope, handlers: ShortcutHandlers): void {
  const handle = useEffectEvent((event: KeyboardEvent) => {
    if (event.repeat || event.defaultPrevented) return;
    const found = comboFor(event, scope);
    if (!found) return;
    if (document.querySelector("dialog[open]")) return;
    if (!found.combo.withModifier && isTyping(event.target)) return;
    const action = handlers[found.shortcut.id];
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

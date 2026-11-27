"use client";

import { shortcutKeys, type ShortcutId } from "./registry";
import { useIsMac } from "./useIsMac";

export function KeyHint({ shortcut, onPrimary = false }: { shortcut: ShortcutId; onPrimary?: boolean }) {
  const mac = useIsMac();
  const tone = onPrimary ? "bg-white/15 text-white/85" : "bg-fill-hover text-secondary";
  return <kbd className={`rounded-sm px-1.25 font-sans text-micro leading-4.25 tabular-nums ${tone}`}>{shortcutKeys(shortcut, mac)}</kbd>;
}

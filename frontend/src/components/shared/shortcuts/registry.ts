import type { Role } from "@/lib/api/types";
import { canDo, canUse, type Action, type Area } from "@/lib/roles";
import { SHARED_TEXT } from "../strings";

export type ShortcutScope = "global" | "queue" | "review";
export type ShortcutId = keyof typeof SHARED_TEXT.shortcuts.labels;

export interface KeyCombo {
  key: string;
  withModifier?: boolean;
}

export interface Shortcut {
  id: ShortcutId;
  scope: ShortcutScope;
  combos: readonly KeyCombo[];
  requires?: Action;
}

export interface KeyPress {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
}

export const SHORTCUTS: readonly Shortcut[] = [
  { id: "search", scope: "global", combos: [{ key: "k", withModifier: true }, { key: "/" }], requires: "search" },
  { id: "shortcuts", scope: "global", combos: [{ key: "?" }] },
  { id: "reviewNext", scope: "queue", combos: [{ key: "n" }] },
  { id: "mine", scope: "queue", combos: [{ key: "m" }] },
  { id: "nextNote", scope: "review", combos: [{ key: "j" }] },
  { id: "previousNote", scope: "review", combos: [{ key: "k" }] },
  { id: "approve", scope: "review", combos: [{ key: "a" }], requires: "approve" },
  { id: "askProvider", scope: "review", combos: [{ key: "p" }], requires: "ask" },
];

export const SCOPE_ORDER: readonly ShortcutScope[] = ["global", "queue", "review"];

const SCOPE_AREAS: Partial<Record<ShortcutScope, Area>> = { queue: "queue", review: "queue" };

const TYPING_TAGS = ["INPUT", "TEXTAREA", "SELECT"];

export function scopeForPath(pathname: string): ShortcutScope {
  if (pathname.startsWith("/notes/")) return "review";
  if (pathname === "/queue") return "queue";
  return "global";
}

export function shortcutsIn(scope: ShortcutScope, role: Role): Shortcut[] {
  const area = SCOPE_AREAS[scope];
  if (area && !canUse(role, area)) return [];
  return SHORTCUTS.filter((shortcut) => shortcut.scope === scope && (!shortcut.requires || canDo(role, shortcut.requires)));
}

export function matchesCombo(combo: KeyCombo, press: KeyPress): boolean {
  if (press.altKey) return false;
  const modified = press.ctrlKey || press.metaKey;
  return Boolean(combo.withModifier) === modified && press.key.toLowerCase() === combo.key;
}

export function comboFor(press: KeyPress, scope: ShortcutScope): { shortcut: Shortcut; combo: KeyCombo } | null {
  for (const shortcut of SHORTCUTS) {
    if (shortcut.scope !== scope) continue;
    const combo = shortcut.combos.find((candidate) => matchesCombo(candidate, press));
    if (combo) return { shortcut, combo };
  }
  return null;
}

export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return TYPING_TAGS.includes(target.tagName) || target.isContentEditable;
}

export function comboKeys(combo: KeyCombo, mac: boolean): string[] {
  const words = SHARED_TEXT.shortcuts;
  const key = combo.key.length === 1 ? combo.key.toUpperCase() : combo.key;
  if (!combo.withModifier) return [key];
  return [mac ? words.modifierMac : words.modifier, key];
}

export function shortcutKeys(id: ShortcutId, mac: boolean): string {
  const combo = SHORTCUTS.find((shortcut) => shortcut.id === id)?.combos[0];
  if (!combo) throw new Error(`No key combination is registered for the ${id} shortcut`);
  return comboKeys(combo, mac).join(SHARED_TEXT.shortcuts.then);
}

export function shortcutTitle(id: ShortcutId, mac: boolean): string {
  const words = SHARED_TEXT.shortcuts;
  return words.titled(words.labels[id], shortcutKeys(id, mac));
}

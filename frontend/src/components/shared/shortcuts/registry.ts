import type { Role } from "@/lib/api/types";
import { canDo, canUse, type Action, type Area } from "@/lib/roles";
import { SHARED_TEXT } from "../strings";

export type ShortcutScope = "global" | "today" | "queue" | "review";
export type ShortcutId = keyof typeof SHARED_TEXT.shortcuts.labels;

export interface KeyCombo {
  key: string;
  withModifier?: boolean;
  withShift?: boolean;
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
  shiftKey: boolean;
}

export const ARROW_DOWN = "arrowdown";
export const ARROW_UP = "arrowup";
export const ARROW_REGION = "data-shortcut-arrows";
const ARROW_KEYS = [ARROW_DOWN, ARROW_UP];
const SHIFTED_KEYS = /^[a-z0-9]$/;

export const SHORTCUTS: readonly Shortcut[] = [
  { id: "search", scope: "global", combos: [{ key: "k", withModifier: true }, { key: "/" }], requires: "search" },
  { id: "shortcuts", scope: "global", combos: [{ key: "?" }] },
  { id: "undo", scope: "global", combos: [{ key: "u" }] },
  { id: "toggleSidebar", scope: "global", combos: [{ key: "[" }] },
  { id: "startReviewing", scope: "today", combos: [{ key: "n" }] },
  { id: "reviewNext", scope: "queue", combos: [{ key: "n" }] },
  { id: "mine", scope: "queue", combos: [{ key: "m" }] },
  { id: "selectRow", scope: "queue", combos: [{ key: "x" }], requires: "decide" },
  { id: "assignSelected", scope: "queue", combos: [{ key: "a" }], requires: "assign" },
  { id: "nextNote", scope: "review", combos: [{ key: "j", withShift: true }] },
  { id: "previousNote", scope: "review", combos: [{ key: "k", withShift: true }] },
  { id: "nextFinding", scope: "review", combos: [{ key: "j" }, { key: ARROW_DOWN }], requires: "decide" },
  { id: "previousFinding", scope: "review", combos: [{ key: "k" }, { key: ARROW_UP }], requires: "decide" },
  { id: "approve", scope: "review", combos: [{ key: "a" }], requires: "approve" },
  { id: "acceptFinding", scope: "review", combos: [{ key: "y" }], requires: "decide" },
  { id: "rejectFinding", scope: "review", combos: [{ key: "n" }], requires: "decide" },
  { id: "acceptSupported", scope: "review", combos: [{ key: "y", withShift: true }], requires: "decide" },
  { id: "editBilled", scope: "review", combos: [{ key: "e" }], requires: "decide" },
  { id: "askProvider", scope: "review", combos: [{ key: "q" }, { key: "p" }], requires: "ask" },
];

export const SCOPE_ORDER: readonly ShortcutScope[] = ["global", "today", "queue", "review"];

const SCOPE_AREAS: Partial<Record<ShortcutScope, Area>> = { today: "queue", queue: "queue", review: "queue" };

const TYPING_TAGS = ["INPUT", "TEXTAREA", "SELECT"];

export function scopeForPath(pathname: string): ShortcutScope {
  if (pathname.startsWith("/notes/")) return "review";
  if (pathname === "/queue") return "queue";
  if (pathname === "/today") return "today";
  return "global";
}

export function shortcutsIn(scope: ShortcutScope, role: Role): Shortcut[] {
  const area = SCOPE_AREAS[scope];
  if (area && !canUse(role, area)) return [];
  return SHORTCUTS.filter((shortcut) => shortcut.scope === scope && (!shortcut.requires || canDo(role, shortcut.requires)));
}

function shiftMatters(combo: KeyCombo): boolean {
  return SHIFTED_KEYS.test(combo.key) || isArrowCombo(combo);
}

export function isArrowCombo(combo: KeyCombo): boolean {
  return ARROW_KEYS.includes(combo.key);
}

export function matchesCombo(combo: KeyCombo, press: KeyPress): boolean {
  if (press.altKey) return false;
  const modified = press.ctrlKey || press.metaKey;
  if (shiftMatters(combo) && Boolean(combo.withShift) !== press.shiftKey) return false;
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

export function arrowsClaimed(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return true;
  return target === document.body || target.closest(`[${ARROW_REGION}]`) !== null;
}

function keyName(key: string): string {
  const named = SHARED_TEXT.shortcuts.keys as Record<string, string>;
  return named[key] ?? (key.length === 1 ? key.toUpperCase() : key);
}

export function comboKeys(combo: KeyCombo, mac: boolean): string[] {
  const words = SHARED_TEXT.shortcuts;
  const keys = [keyName(combo.key)];
  if (combo.withShift) keys.unshift(words.shift);
  if (combo.withModifier) keys.unshift(mac ? words.modifierMac : words.modifier);
  return keys;
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

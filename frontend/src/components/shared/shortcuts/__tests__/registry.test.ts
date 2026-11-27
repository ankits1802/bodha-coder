import { describe, expect, it } from "vitest";
import {
  comboFor,
  comboKeys,
  scopeForPath,
  SCOPE_ORDER,
  SHORTCUTS,
  shortcutKeys,
  shortcutsIn,
  shortcutTitle,
  type KeyPress,
} from "../registry";

function press(key: string, extra: Partial<KeyPress> = {}): KeyPress {
  return { key, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...extra };
}

describe("shortcut registry", () => {
  it("tells Ctrl or Command K, which searches, from K, which moves between findings, and Shift K, which goes to the previous note", () => {
    expect(comboFor(press("k", { ctrlKey: true }), "global")?.shortcut.id).toBe("search");
    expect(comboFor(press("k", { metaKey: true }), "global")?.shortcut.id).toBe("search");
    expect(comboFor(press("/"), "global")?.shortcut.id).toBe("search");
    expect(comboFor(press("?", { shiftKey: true }), "global")?.shortcut.id).toBe("shortcuts");
    expect(comboFor(press("k"), "global")).toBeNull();
    expect(comboFor(press("k"), "review")?.shortcut.id).toBe("previousFinding");
    expect(comboFor(press("K", { shiftKey: true }), "review")?.shortcut.id).toBe("previousNote");
    expect(comboFor(press("J", { shiftKey: true }), "review")?.shortcut.id).toBe("nextNote");
    expect(comboFor(press("k", { ctrlKey: true }), "review")).toBeNull();
    expect(comboFor(press("j", { altKey: true }), "review")).toBeNull();
  });

  it("moves between findings with J and K or the arrow keys, and accepts all supported with Shift Y", () => {
    expect(comboFor(press("j"), "review")?.shortcut.id).toBe("nextFinding");
    expect(comboFor(press("ArrowDown"), "review")?.shortcut.id).toBe("nextFinding");
    expect(comboFor(press("ArrowUp"), "review")?.shortcut.id).toBe("previousFinding");
    expect(comboFor(press("ArrowDown", { shiftKey: true }), "review")).toBeNull();
    expect(comboFor(press("y"), "review")?.shortcut.id).toBe("acceptFinding");
    expect(comboFor(press("Y", { shiftKey: true }), "review")?.shortcut.id).toBe("acceptSupported");
    expect(comboFor(press("e"), "review")?.shortcut.id).toBe("editBilled");
    expect(comboFor(press("E", { shiftKey: true }), "review")).toBeNull();
  });

  it("gives each key one meaning on every screen", () => {
    for (const scope of SCOPE_ORDER) {
      const keys = SHORTCUTS.filter((shortcut) => shortcut.scope === scope || shortcut.scope === "global").flatMap((shortcut) =>
        shortcut.combos.map((combo) => `${combo.withModifier ? "mod+" : ""}${combo.withShift ? "shift+" : ""}${combo.key}`),
      );
      expect(new Set(keys).size).toBe(keys.length);
    }
  });

  it("finds the screen from the path", () => {
    expect(scopeForPath("/notes/note-1")).toBe("review");
    expect(scopeForPath("/queue")).toBe("queue");
    expect(scopeForPath("/today")).toBe("today");
    expect(scopeForPath("/today/x")).toBe("global");
    expect(scopeForPath("/queued")).toBe("global");
  });

  it("lists only the shortcuts a role may use", () => {
    expect(shortcutsIn("review", "coder").map((shortcut) => shortcut.id)).toEqual([
      "nextNote",
      "previousNote",
      "nextFinding",
      "previousFinding",
      "approve",
      "acceptFinding",
      "rejectFinding",
      "acceptSupported",
      "editBilled",
      "askProvider",
    ]);
    expect(shortcutsIn("review", "cdi").map((shortcut) => shortcut.id)).toEqual([
      "nextNote",
      "previousNote",
      "nextFinding",
      "previousFinding",
      "acceptFinding",
      "rejectFinding",
      "acceptSupported",
      "editBilled",
      "askProvider",
    ]);
    expect(shortcutsIn("review", "biller").map((shortcut) => shortcut.id)).toEqual(["nextNote", "previousNote"]);
    expect(shortcutsIn("global", "viewer").map((shortcut) => shortcut.id)).toEqual(["shortcuts", "undo", "toggleSidebar"]);
    expect(shortcutsIn("today", "coder").map((shortcut) => shortcut.id)).toEqual(["startReviewing"]);
    expect(shortcutsIn("today", "viewer")).toEqual([]);
    expect(shortcutsIn("queue", "viewer")).toEqual([]);
    expect(shortcutsIn("queue", "biller").map((shortcut) => shortcut.id)).toEqual(["reviewNext", "mine"]);
  });

  it("names the modifier key of the platform", () => {
    expect(comboKeys({ key: "k", withModifier: true }, true)).toEqual(["⌘", "K"]);
    expect(comboKeys({ key: "k", withModifier: true }, false)).toEqual(["Ctrl", "K"]);
    expect(comboKeys({ key: "/" }, false)).toEqual(["/"]);
    expect(comboKeys({ key: "y", withShift: true }, true)).toEqual(["Shift", "Y"]);
    expect(comboKeys({ key: "arrowdown" }, false)).toEqual(["↓"]);
  });

  it("titles a control with its label and first key, as the overlay lists them", () => {
    expect(shortcutTitle("previousNote", false)).toBe("Previous note (Shift+K)");
    expect(shortcutTitle("nextNote", true)).toBe("Next note (Shift+J)");
    expect(shortcutTitle("acceptSupported", false)).toBe("Accept all supported (Shift+Y)");
    expect(shortcutKeys("approve", false)).toBe("A");
    expect(shortcutKeys("askProvider", true)).toBe("Q");
    expect(comboFor(press("p"), "review")?.shortcut.id).toBe("askProvider");
    expect(comboFor(press("n"), "review")?.shortcut.id).toBe("rejectFinding");
    expect(comboFor(press("n"), "today")?.shortcut.id).toBe("startReviewing");
    expect(shortcutKeys("search", true)).toBe("⌘+K");
    expect(shortcutKeys("search", false)).toBe("Ctrl+K");
  });
});

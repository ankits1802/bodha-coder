export type TourMove = "next" | "back" | "skip";

const MOVES: Readonly<Record<string, TourMove>> = { ArrowRight: "next", ArrowLeft: "back", Escape: "skip" };

export function moveFor(key: string, onControl: boolean): TourMove | null {
  if (key === "Enter") return onControl ? null : "next";
  return MOVES[key] ?? null;
}

export function focusWrapTarget(controls: readonly HTMLElement[], active: Element | null, backwards: boolean): HTMLElement | null {
  const first = controls[0];
  const last = controls[controls.length - 1];
  if (!first || !last) return null;
  const inside = active !== null && controls.includes(active as HTMLElement);
  if (backwards) return !inside || active === first ? last : null;
  return !inside || active === last ? first : null;
}

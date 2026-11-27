const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const FINE_POINTER = "(pointer: fine)";
const WIDE_SCREEN = "(min-width: 64rem)";

function matches(query: string): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

export function prefersReducedMotion(): boolean {
  return matches(REDUCED_MOTION);
}

export function hasFinePointer(): boolean {
  return matches(FINE_POINTER);
}

export function isWideScreen(): boolean {
  return matches(WIDE_SCREEN);
}

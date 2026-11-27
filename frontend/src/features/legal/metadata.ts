import type { Metadata } from "next";

export function legalRobots(draft: boolean): Metadata["robots"] {
  return draft ? { index: false, follow: true } : { index: true, follow: true };
}

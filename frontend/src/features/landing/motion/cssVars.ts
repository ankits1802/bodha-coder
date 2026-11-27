import type { CSSProperties } from "react";

export function cssVars(values: Record<`--${string}`, string | number>): CSSProperties {
  return values as CSSProperties;
}

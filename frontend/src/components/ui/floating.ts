export const FLOAT_GAP = 4;
export const FLOAT_EDGE = 8;

export interface Anchor {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface Viewport {
  width: number;
  height: number;
}

export type FloatAlign = "auto" | "end";

export interface FloatingStyle {
  top?: number;
  bottom?: number;
  left?: number;
  right?: number;
  maxHeight: number;
  maxWidth: number;
}

export function floatingStyle(anchor: Anchor, viewport: Viewport, height: number, align: FloatAlign = "auto"): FloatingStyle {
  const below = viewport.height - anchor.bottom - FLOAT_GAP - FLOAT_EDGE;
  const above = anchor.top - FLOAT_GAP - FLOAT_EDGE;
  const vertical =
    below >= height || below >= above
      ? { top: anchor.bottom + FLOAT_GAP, maxHeight: Math.max(below, 0) }
      : { bottom: viewport.height - anchor.top + FLOAT_GAP, maxHeight: above };
  const startRoom = viewport.width - anchor.left - FLOAT_EDGE;
  const endRoom = anchor.right - FLOAT_EDGE;
  const horizontal =
    align === "auto" && startRoom >= endRoom
      ? { left: Math.max(anchor.left, FLOAT_EDGE), maxWidth: startRoom }
      : { right: Math.max(viewport.width - anchor.right, FLOAT_EDGE), maxWidth: endRoom };
  return { ...vertical, ...horizontal };
}

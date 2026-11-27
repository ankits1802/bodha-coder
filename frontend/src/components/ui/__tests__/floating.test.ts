import { describe, expect, it } from "vitest";
import { floatingStyle } from "../floating";

const VIEWPORT = { width: 1000, height: 800 };

describe("floatingStyle", () => {
  it("opens below and from the left edge when there is room", () => {
    const anchor = { top: 100, bottom: 136, left: 40, right: 240 };
    expect(floatingStyle(anchor, VIEWPORT, 200)).toEqual({ top: 140, maxHeight: 652, left: 40, maxWidth: 952 });
  });

  it("flips above and anchors to the right edge near the bottom right corner", () => {
    const anchor = { top: 700, bottom: 736, left: 800, right: 980 };
    expect(floatingStyle(anchor, VIEWPORT, 300)).toEqual({ bottom: 104, maxHeight: 688, right: 20, maxWidth: 972 });
  });

  it("stays below when neither side fits but below has more room", () => {
    const anchor = { top: 40, bottom: 740, left: 40, right: 240 };
    expect(floatingStyle(anchor, VIEWPORT, 300)).toEqual({ top: 744, maxHeight: 48, left: 40, maxWidth: 952 });
  });

  it("aligns to the end of the anchor when asked", () => {
    const anchor = { top: 100, bottom: 136, left: 40, right: 240 };
    expect(floatingStyle(anchor, VIEWPORT, 200, "end")).toEqual({ top: 140, maxHeight: 652, right: 760, maxWidth: 232 });
  });
});

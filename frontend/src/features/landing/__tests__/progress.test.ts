import { describe, expect, it } from "vitest";
import { actFor, enterProgress, pinProgress, throughProgress } from "../motion/progress";

describe("scroll progress", () => {
  it("runs the entrance from 80% to 15% of the viewport", () => {
    expect(enterProgress(1000, 1000)).toBe(0);
    expect(enterProgress(800, 1000)).toBe(0);
    expect(enterProgress(475, 1000)).toBeCloseTo(0.5);
    expect(enterProgress(150, 1000)).toBe(1);
    expect(enterProgress(-400, 1000)).toBe(1);
  });

  it("runs a pinned section while it scrolls past the viewport", () => {
    expect(pinProgress(100, 3400, 1000)).toBe(0);
    expect(pinProgress(-1200, 3400, 1000)).toBe(0.5);
    expect(pinProgress(-3000, 3400, 1000)).toBe(1);
    expect(pinProgress(10, 900, 1000)).toBe(0);
    expect(pinProgress(-10, 900, 1000)).toBe(1);
  });

  it("fills as a line at 85% of the viewport passes through, over at least 60% of the viewport", () => {
    expect(throughProgress(1000, 300, 1000)).toBe(0);
    expect(throughProgress(900, 300, 1000)).toBe(0);
    expect(throughProgress(550, 300, 1000)).toBeCloseTo(0.5);
    expect(throughProgress(200, 300, 1000)).toBe(1);
    expect(throughProgress(-150, 2000, 1000)).toBeCloseTo(0.5);
    expect(throughProgress(-1500, 2000, 1000)).toBe(1);
  });

  it("splits progress evenly between acts and holds the last", () => {
    expect([0, 0.33, 0.34, 0.66, 0.67, 1].map((progress) => actFor(progress, 3))).toEqual([0, 0, 1, 1, 2, 2]);
  });
});

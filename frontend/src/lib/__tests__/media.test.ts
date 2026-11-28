import { afterEach, describe, expect, it, vi } from "vitest";
import { prefersReducedMotion } from "@/lib/media";

const REDUCED = "(prefers-reduced-motion: reduce)";

function systemReducesMotion(reduces: boolean): void {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: reduces && query === REDUCED, media: query }));
}

describe("prefersReducedMotion", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.removeAttribute("data-motion");
  });

  it("follows the system when the person left it on System", () => {
    systemReducesMotion(true);
    expect(prefersReducedMotion()).toBe(true);
    systemReducesMotion(false);
    expect(prefersReducedMotion()).toBe(false);
  });

  it("reduces motion when the person turned Reduce motion on, whatever the system says", () => {
    systemReducesMotion(false);
    document.documentElement.setAttribute("data-motion", "reduce");
    expect(prefersReducedMotion()).toBe(true);
  });

  it("keeps motion when the person turned Reduce motion off, whatever the system says", () => {
    systemReducesMotion(true);
    document.documentElement.setAttribute("data-motion", "full");
    expect(prefersReducedMotion()).toBe(false);
  });
});

import { afterEach, describe, expect, it } from "vitest";
import type { Appearance } from "@/lib/api/types";
import {
  APPEARANCE_COOKIE,
  appearanceAttributes,
  appearanceCookieValue,
  appearanceFromCookie,
  applyAppearance,
  chosenMotion,
  SYSTEM_APPEARANCE,
} from "@/lib/appearance";

const DARK_LARGER_STILL: Appearance = { theme: "dark", text_size: "larger", reduce_motion: "on" };
const LIGHT_LARGE_MOVING: Appearance = { theme: "light", text_size: "large", reduce_motion: "off" };
const ATTRIBUTES = ["data-theme", "data-text-size", "data-motion"];

function forgetDevice(): void {
  for (const name of ATTRIBUTES) document.documentElement.removeAttribute(name);
  document.cookie = `${APPEARANCE_COOKIE}=; Path=/; Max-Age=0`;
}

describe("the appearance kept on a device", () => {
  it("reads theme, text size and motion in that order", () => {
    expect(appearanceFromCookie("dark.larger.on")).toEqual(DARK_LARGER_STILL);
    expect(appearanceFromCookie("light.large.off")).toEqual(LIGHT_LARGE_MOVING);
  });

  it("uses System for a device with nothing kept and for any part it does not know", () => {
    expect(appearanceFromCookie(undefined)).toEqual(SYSTEM_APPEARANCE);
    expect(appearanceFromCookie("")).toEqual(SYSTEM_APPEARANCE);
    expect(appearanceFromCookie("sepia.large.sideways")).toEqual({ theme: "system", text_size: "large", reduce_motion: "system" });
    expect(appearanceFromCookie("dark")).toEqual({ theme: "dark", text_size: "default", reduce_motion: "system" });
  });

  it("writes the same three parts it reads", () => {
    expect(appearanceCookieValue(DARK_LARGER_STILL)).toBe("dark.larger.on");
    expect(appearanceCookieValue(SYSTEM_APPEARANCE)).toBe("system.default.system");
  });
});

describe("the attributes on the page", () => {
  it("are absent for System, so the system settings decide", () => {
    expect(appearanceAttributes(SYSTEM_APPEARANCE)).toEqual({});
  });

  it("name each choice that departs from System", () => {
    expect(appearanceAttributes(DARK_LARGER_STILL)).toEqual({ "data-theme": "dark", "data-text-size": "larger", "data-motion": "reduce" });
    expect(appearanceAttributes(LIGHT_LARGE_MOVING)).toEqual({ "data-theme": "light", "data-text-size": "large", "data-motion": "full" });
  });
});

describe("applyAppearance", () => {
  afterEach(forgetDevice);

  it("marks the page at once and keeps the choice on the device", () => {
    applyAppearance(DARK_LARGER_STILL);
    const root = document.documentElement;
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(root).toHaveAttribute("data-text-size", "larger");
    expect(root).toHaveAttribute("data-motion", "reduce");
    expect(document.cookie).toContain(`${APPEARANCE_COOKIE}=dark.larger.on`);
    expect(chosenMotion()).toBe("on");
  });

  it("clears the marks when the person goes back to System", () => {
    applyAppearance(DARK_LARGER_STILL);
    applyAppearance(SYSTEM_APPEARANCE);
    const root = document.documentElement;
    for (const name of ATTRIBUTES) expect(root).not.toHaveAttribute(name);
    expect(document.cookie).toContain(`${APPEARANCE_COOKIE}=system.default.system`);
    expect(chosenMotion()).toBe("system");
  });

  it("reads Reduce motion off from the page", () => {
    applyAppearance(LIGHT_LARGE_MOVING);
    expect(chosenMotion()).toBe("off");
  });
});

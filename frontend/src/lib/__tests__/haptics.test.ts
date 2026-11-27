import { afterEach, describe, expect, it, vi } from "vitest";
import { haptic } from "@/lib/haptics";

function setNavigator(key: "vibrate" | "maxTouchPoints", value: unknown): void {
  Object.defineProperty(navigator, key, { value, configurable: true });
}

describe("haptic", () => {
  afterEach(() => {
    setNavigator("vibrate", undefined);
    setNavigator("maxTouchPoints", 0);
  });

  it("vibrates with the pattern for the gesture where vibration exists", () => {
    const vibrate = vi.fn(() => true);
    setNavigator("vibrate", vibrate);
    haptic("success");
    haptic("tap");
    expect(vibrate.mock.calls).toEqual([[[12, 60, 18]], [[8]]]);
  });

  it("ticks one hidden native switch on touch devices without vibration", () => {
    setNavigator("maxTouchPoints", 5);
    const click = vi.spyOn(HTMLElement.prototype, "click");
    haptic("select");
    haptic("select");
    const switches = document.querySelectorAll("input[switch]");
    expect(switches).toHaveLength(1);
    expect(switches[0]?.closest("label")).toHaveAttribute("aria-hidden", "true");
    expect(click).toHaveBeenCalledTimes(2);
  });

  it("does nothing on a desktop without vibration", () => {
    const click = vi.spyOn(HTMLElement.prototype, "click");
    haptic("tap");
    expect(click).not.toHaveBeenCalled();
  });
});

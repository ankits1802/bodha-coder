import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { startIdleTimer } from "@/lib/session/idle";

const MINUTE = 60_000;

function press(): void {
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
}

describe("idle sign-out timer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("signs out once the limit passes without activity", () => {
    const onIdle = vi.fn();
    const stop = startIdleTimer({ minutes: 15, onIdle });

    vi.advanceTimersByTime(15 * MINUTE - 1);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onIdle).toHaveBeenCalledTimes(1);
    stop();
  });

  it("restarts the countdown on activity", () => {
    const onIdle = vi.fn();
    const stop = startIdleTimer({ minutes: 15, onIdle });

    vi.advanceTimersByTime(10 * MINUTE);
    press();
    vi.advanceTimersByTime(10 * MINUTE);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(5 * MINUTE);
    expect(onIdle).toHaveBeenCalledTimes(1);
    stop();
  });

  it("does not let late activity extend an expired session", () => {
    let clock = 1_000_000;
    const onIdle = vi.fn();
    const stop = startIdleTimer({ minutes: 5, onIdle, now: () => clock });

    clock += 6 * MINUTE;
    press();

    expect(onIdle).toHaveBeenCalledTimes(1);
    stop();
  });

  it("fires only once and stops listening afterwards", () => {
    const onIdle = vi.fn();
    startIdleTimer({ minutes: 5, onIdle });

    vi.advanceTimersByTime(5 * MINUTE);
    press();
    vi.advanceTimersByTime(30 * MINUTE);

    expect(onIdle).toHaveBeenCalledTimes(1);
  });

  it("never fires after it is stopped", () => {
    const onIdle = vi.fn();
    const stop = startIdleTimer({ minutes: 5, onIdle });

    stop();
    vi.advanceTimersByTime(30 * MINUTE);

    expect(onIdle).not.toHaveBeenCalled();
  });
});

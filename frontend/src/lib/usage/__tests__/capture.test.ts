import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import { FLUSH_EVERY_MS, flushUsage, startUsageCapture, stepOf } from "../capture";
import { UsageRecorder } from "../recorder";

function recorder(): UsageRecorder {
  let ids = 0;
  return new UsageRecorder({ clock: () => Date.now(), newId: () => `event-${(ids += 1)}`, sessionKey: () => "user-1:practice-1" });
}

function finishedUpload(target: UsageRecorder): void {
  const upload = target.start("upload");
  vi.advanceTimersByTime(2_000);
  target.end(upload, "completed");
}

describe("stepOf", () => {
  it("reads the nearest marked area and ignores names outside the step vocabulary", () => {
    document.body.innerHTML = `
      <section data-usage-step="findings"><button id="inside">Accept</button></section>
      <div data-usage-step="patient-name"><span id="odd">x</span></div>
      <p id="outside">plain</p>`;
    expect(stepOf(document.getElementById("inside"))).toBe("findings");
    expect(stepOf(document.getElementById("odd"))).toBeNull();
    expect(stepOf(document.getElementById("outside"))).toBeNull();
    expect(stepOf(null)).toBeNull();
  });
});

describe("startUsageCapture", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = `<div data-usage-step="claim"><button id="approve">Approve</button></div>`;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts inputs without sending anything until the interval, then sends one batch", async () => {
    const usage = recorder();
    const send = vi.fn().mockResolvedValue(undefined);
    const stop = startUsageCapture(usage, send, { window, document });
    const review = usage.start("note_review");
    const button = document.getElementById("approve") as HTMLButtonElement;
    for (let press = 0; press < 20; press += 1) button.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true }));
    button.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    usage.end(review, "completed");
    expect(send).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(FLUSH_EVERY_MS);

    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith([expect.objectContaining({ task: "note_review", key_inputs: 20, pointer_inputs: 1 })], false);
    stop();
  });

  it("sends what is left with keepalive when the page is hidden", () => {
    const usage = recorder();
    const send = vi.fn().mockResolvedValue(undefined);
    const stop = startUsageCapture(usage, send, { window, document });
    finishedUpload(usage);

    window.dispatchEvent(new Event("pagehide"));

    expect(send).toHaveBeenCalledWith([expect.objectContaining({ task: "upload" })], true);
    stop();
  });

  it("stops listening when stopped", () => {
    const usage = recorder();
    const stop = startUsageCapture(usage, vi.fn().mockResolvedValue(undefined), { window, document });
    stop();
    const review = usage.start("note_review");
    document.getElementById("approve")?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true }));
    vi.advanceTimersByTime(2_000);
    usage.end(review, "left");

    expect(usage.take()).toEqual([expect.objectContaining({ key_inputs: 0 })]);
  });
});

describe("flushUsage", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("keeps a batch the server could not take for the next flush, and drops one it refused", async () => {
    const usage = recorder();
    finishedUpload(usage);
    const unavailable = vi.fn().mockRejectedValue(new ApiError(503, "unavailable", "try again"));
    flushUsage(usage, unavailable, false);
    await vi.runAllTimersAsync();
    expect(usage.take()).toHaveLength(1);

    finishedUpload(usage);
    const refused = vi.fn().mockRejectedValue(new ApiError(422, "invalid", "a stall lasts at least 60 seconds"));
    flushUsage(usage, refused, false);
    await vi.runAllTimersAsync();
    expect(usage.take()).toEqual([]);
  });
});

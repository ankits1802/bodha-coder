import { describe, expect, it, vi } from "vitest";
import { currentToast, dismissToast, runToastAction, showToast } from "../toastStore";

describe("toast store", () => {
  it("shows the latest toast and dismisses only the one asked for", () => {
    showToast("Approved Reyes Marisol");
    const first = currentToast();
    showToast("4 approved");
    expect(currentToast()?.message).toBe("4 approved");
    dismissToast(first?.id);
    expect(currentToast()?.message).toBe("4 approved");
    dismissToast();
    expect(currentToast()).toBeNull();
  });

  it("runs the undo action once and closes the toast", () => {
    const undo = vi.fn();
    showToast("Approved Reyes Marisol", { label: "Undo", run: undo });
    expect(runToastAction()).toBe(true);
    expect(runToastAction()).toBe(false);
    expect(undo).toHaveBeenCalledTimes(1);
    expect(currentToast()).toBeNull();
  });
});

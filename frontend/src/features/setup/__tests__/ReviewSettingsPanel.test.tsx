import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { saveReviewSettings } from "@/lib/api/practice";
import { ReviewSettingsPanel } from "../ReviewSettingsPanel";

vi.mock("@/lib/api/practice", () => ({ saveReviewSettings: vi.fn() }));

const OFF = { confirm_level_changes: false, hold_until_confirmed: false };
const CONFIRM = "Ask the provider to confirm E/M level changes";
const HOLD = "Hold the claim until confirmed";

describe("level change settings", () => {
  it("starts off, keeps hold unavailable until confirmation is on, and saves both", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    vi.mocked(saveReviewSettings).mockResolvedValue({ confirm_level_changes: true, hold_until_confirmed: true });
    render(<ReviewSettingsPanel settings={OFF} onSaved={onSaved} />);
    expect(screen.getByRole("switch", { name: CONFIRM })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("switch", { name: HOLD })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    await user.click(screen.getByRole("switch", { name: CONFIRM }));
    await user.click(screen.getByRole("switch", { name: HOLD }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(saveReviewSettings).toHaveBeenCalledWith({ confirm_level_changes: true, hold_until_confirmed: true });
    expect(onSaved).toHaveBeenCalled();
  });

  it("turns hold off with confirmation", async () => {
    const user = userEvent.setup();
    render(<ReviewSettingsPanel settings={{ confirm_level_changes: true, hold_until_confirmed: true }} onSaved={vi.fn()} />);

    await user.click(screen.getByRole("switch", { name: CONFIRM }));

    expect(screen.getByRole("switch", { name: HOLD })).toHaveAttribute("aria-checked", "false");
    expect(screen.getByRole("switch", { name: HOLD })).toBeDisabled();
  });
});

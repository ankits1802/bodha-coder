import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { haptic } from "@/lib/haptics";
import { LandingPage } from "../LandingPage";
import { LANDING_TEXT } from "../strings";

vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

describe("LandingPage", () => {
  it("reads as one headline, the three acts and the figures", () => {
    render(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(LANDING_TEXT.hero.title);
    expect(screen.getByRole("heading", { level: 2, name: "Upload. Review. Defend." })).toBeInTheDocument();
    for (const act of LANDING_TEXT.story.acts) {
      expect(screen.getByRole("heading", { level: 3, name: act.title })).toBeInTheDocument();
    }
    expect(screen.getAllByText("100%")).toHaveLength(2);
    expect(screen.getByRole("heading", { level: 2, name: LANDING_TEXT.demo.title })).toBeInTheDocument();
  });

  it("turns the evidence off and back on with a haptic tick", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    const toggle = screen.getByRole("switch", { name: LANDING_TEXT.product.evidence });
    const scope = toggle.closest("[data-evidence]");
    await user.click(toggle);
    expect(scope).toHaveAttribute("data-evidence", "off");
    expect(toggle).toHaveAttribute("aria-checked", "false");
    await user.click(toggle);
    expect(scope).toHaveAttribute("data-evidence", "on");
    expect(vi.mocked(haptic).mock.calls).toEqual([["select"], ["select"]]);
  });

  it("approves the sample with a success haptic and undoes it", async () => {
    const user = userEvent.setup();
    render(<LandingPage />);
    await user.click(screen.getByRole("button", { name: LANDING_TEXT.numbers.approve }));
    expect(screen.getByRole("button", { name: LANDING_TEXT.numbers.approved })).toHaveAttribute("aria-pressed", "true");
    expect(vi.mocked(haptic)).toHaveBeenLastCalledWith("success");
    await user.click(screen.getByRole("button", { name: LANDING_TEXT.numbers.approved }));
    expect(screen.getByRole("button", { name: LANDING_TEXT.numbers.approve })).toHaveAttribute("aria-pressed", "false");
  });
});

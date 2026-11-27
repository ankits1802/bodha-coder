import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { haptic } from "@/lib/haptics";
import { DeskTabs } from "../desks/DeskTabs";
import { nextTabIndex } from "../tabs/tabKeys";

vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

const TABS = [
  { key: "alpha", label: "Alpha", panel: <p>Panel A</p> },
  { key: "beta", label: "Beta", panel: <p>Panel B</p> },
  { key: "gamma", label: "Gamma", panel: <p>Panel C</p> },
];

describe("tab keys", () => {
  it("moves right and left with wrap-around, and jumps with Home and End", () => {
    expect(nextTabIndex("ArrowRight", 0, 6)).toBe(1);
    expect(nextTabIndex("ArrowRight", 5, 6)).toBe(0);
    expect(nextTabIndex("ArrowLeft", 0, 6)).toBe(5);
    expect(nextTabIndex("ArrowLeft", 3, 6)).toBe(2);
    expect(nextTabIndex("Home", 4, 6)).toBe(0);
    expect(nextTabIndex("End", 1, 6)).toBe(5);
    expect(nextTabIndex("ArrowDown", 1, 6)).toBeNull();
    expect(nextTabIndex("Enter", 1, 6)).toBeNull();
  });
});

describe("DeskTabs", () => {
  beforeEach(() => {
    vi.mocked(haptic).mockClear();
  });

  it("follows the tabs pattern: one tab in the tab order, its panel labelled by it", () => {
    render(<DeskTabs label="Roles" tabs={TABS} />);
    expect(screen.getByRole("tablist", { name: "Roles" })).toBeInTheDocument();
    const [alpha, beta, gamma] = screen.getAllByRole("tab");
    expect(alpha).toHaveAttribute("aria-selected", "true");
    expect(alpha).toHaveAttribute("tabindex", "0");
    expect(beta).toHaveAttribute("tabindex", "-1");
    expect(gamma).toHaveAttribute("tabindex", "-1");
    const panel = screen.getByRole("tabpanel", { name: "Alpha" });
    expect(panel).toHaveTextContent("Panel A");
    expect(alpha).toHaveAttribute("aria-controls", panel.id);
    expect(screen.getByText("Panel B")).not.toBeVisible();
  });

  it("selects and focuses with the arrow keys, Home and End", async () => {
    const user = userEvent.setup();
    render(<DeskTabs label="Roles" tabs={TABS} />);
    await user.click(screen.getByRole("tab", { name: "Alpha" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel B");
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Gamma" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Gamma" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Home}");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel A");
    expect(screen.getByText("Panel C")).not.toBeVisible();
  });

  it("ticks a haptic only when the selection changes", async () => {
    const user = userEvent.setup();
    render(<DeskTabs label="Roles" tabs={TABS} />);
    await user.click(screen.getByRole("tab", { name: "Alpha" }));
    expect(vi.mocked(haptic)).not.toHaveBeenCalled();
    await user.click(screen.getByRole("tab", { name: "Gamma" }));
    expect(vi.mocked(haptic).mock.calls).toEqual([["select"]]);
    expect(screen.getByRole("tabpanel", { name: "Gamma" })).toHaveTextContent("Panel C");
  });
});

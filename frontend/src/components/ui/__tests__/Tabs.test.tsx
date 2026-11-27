import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Tabs, type TabActivation } from "../Tabs";

const TABS = [
  { value: "setup", label: "Setup" },
  { value: "team", label: "Team" },
  { value: "plan", label: "Plan" },
];

function Harness({ activation, onChange }: { activation: TabActivation; onChange: (value: string) => void }) {
  const [value, setValue] = useState("setup");
  return (
    <Tabs
      label="Settings"
      tabs={TABS}
      value={value}
      activation={activation}
      onChange={(next) => {
        onChange(next);
        setValue(next);
      }}
    >
      <p>{value} panel</p>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("selects with the arrows at once when activation is automatic", async () => {
    const onChange = vi.fn();
    render(<Harness activation="automatic" onChange={onChange} />);
    screen.getByRole("tab", { name: "Setup" }).focus();
    await userEvent.setup().keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenCalledWith("team");
    expect(screen.getByRole("tab", { name: "Team" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Team" })).toHaveTextContent("team panel");
  });

  it("only moves focus with the arrows, Home and End when activation is manual, and selects on Enter", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness activation="manual" onChange={onChange} />);
    screen.getByRole("tab", { name: "Setup" }).focus();
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Plan" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Setup" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Plan" })).toHaveFocus();
    expect(onChange).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("plan");
  });

  it("keeps only the selected tab in the tab order", () => {
    render(<Harness activation="manual" onChange={vi.fn()} />);
    expect(screen.getByRole("tab", { name: "Setup" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Team" })).toHaveAttribute("tabindex", "-1");
  });
});

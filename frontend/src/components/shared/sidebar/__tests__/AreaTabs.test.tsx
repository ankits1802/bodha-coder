import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CODER } from "@/features/queue/__tests__/fixtures";
import type { Role } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { AreaTabs } from "../AreaTabs";

const navigation = vi.hoisted(() => ({ push: vi.fn(), pathname: "/settings/setup" }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation, usePathname: () => navigation.pathname }));

function show(role: Role, navKey: string, pathname: string, billingOnly = false): void {
  navigation.pathname = pathname;
  setSession({ access_token: "token", user: { ...CODER, role, billing_only: billingOnly } });
  render(
    <AreaTabs navKey={navKey}>
      <h1>Page</h1>
    </AreaTabs>,
  );
}

describe("AreaTabs", () => {
  beforeEach(() => navigation.push.mockReset());
  afterEach(() => clearSession());

  it("shows an admin every settings tab with the current page selected, and opens another only on Enter", async () => {
    show("admin", "settings", "/settings/team");
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Setup", "Team", "Plan", "Security"]);
    expect(screen.getByRole("tab", { name: "Team" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Team" })).toHaveTextContent("Page");
    const user = userEvent.setup();
    screen.getByRole("tab", { name: "Team" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(navigation.push).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(navigation.push).toHaveBeenCalledWith("/settings/plan");
  });

  it("selects the most specific tab for a page under a tab", () => {
    show("compliance", "insights", "/insights/quality/review/sample-1");
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Overview", "Quality", "Access log"]);
    expect(screen.getByRole("tab", { name: "Quality" })).toHaveAttribute("aria-selected", "true");
  });

  it("draws no tab row when the role can open only one tab", () => {
    show("viewer", "insights", "/insights");
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Page" })).toBeInTheDocument();
  });

  it("keeps a billing-only admin to the plan page without tabs", () => {
    show("admin", "settings", "/settings/plan", true);
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });
});

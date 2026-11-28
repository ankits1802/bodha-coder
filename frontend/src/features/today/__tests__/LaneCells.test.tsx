import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { LaneCounts, ProviderReasonCounts, Role } from "@/lib/api/types";
import type { SessionUser } from "@/lib/roles";
import { LaneCells } from "../components/LaneCells";

const COUNTS: LaneCounts = {
  approve: { total: 3, due_soon: 1 },
  coder: { total: 4, due_soon: 2 },
  provider: { total: 5, due_soon: 1 },
  compliance: { total: 2, due_soon: 0 },
};
const REASONS: ProviderReasonCounts = {
  questions: { total: 2, due_soon: 1 },
  waiting_on_provider: { total: 3, due_soon: 0 },
};

function person(role: Role, billingOnly = false): SessionUser {
  return { role, billing_only: billingOnly, organizations: [] };
}

function tiles(): { name: string; href: string | null }[] {
  const section = screen.getByRole("region", { name: "Waiting for review" });
  return within(section)
    .queryAllByRole("link")
    .map((link) => ({ name: link.getAttribute("aria-label") ?? "", href: link.getAttribute("href") }));
}

describe("Today lane tiles", () => {
  it("opens each lane of the queue, the provider lane split into questions to send and waiting on the provider", () => {
    render(<LaneCells counts={COUNTS} reasons={REASONS} user={person("coder")} />);
    expect(tiles()).toEqual([
      { name: "Ready to approve, 3, 1 due within a day", href: "/queue?lane=approve" },
      { name: "Needs a coder, 4, 2 due within a day", href: "/queue?lane=coder" },
      { name: "Questions to send, 2, 1 due within a day", href: "/queue?lane=provider&reason=questions" },
      { name: "Waiting on provider, 3, 0 due within a day", href: "/queue?lane=provider&reason=waiting_on_provider" },
      { name: "Compliance, 2, 0 due within a day", href: "/queue?lane=compliance" },
    ]);
  });

  it("names each tile by its lane, its count and what is due soon", () => {
    render(<LaneCells counts={COUNTS} reasons={REASONS} user={person("coder")} />);
    expect(screen.getByRole("link", { name: "Needs a coder, 4, 2 due within a day" })).toHaveAttribute("href", "/queue?lane=coder");
  });

  it("sends compliance to its own screen for a compliance reviewer", () => {
    render(<LaneCells counts={COUNTS} reasons={REASONS} user={person("compliance")} />);
    expect(tiles().at(-1)).toEqual({ name: "Compliance, 2, 0 due within a day", href: "/compliance" });
  });

  it("leaves every tile as plain text for a viewer and in a billing-only session", () => {
    const { unmount } = render(<LaneCells counts={COUNTS} reasons={REASONS} user={person("viewer")} />);
    expect(tiles()).toEqual([]);
    expect(screen.getByText("Questions to send")).toBeInTheDocument();
    unmount();
    render(<LaneCells counts={COUNTS} reasons={REASONS} user={person("admin", true)} />);
    expect(tiles()).toEqual([]);
    expect(screen.getByText("4")).toBeInTheDocument();
  });
});

import { render, screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { LaneCounts, ProviderReasonCounts } from "@/lib/api/types";
import { LaneCells } from "../components/LaneCells";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

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

function tiles(): { name: string; href: string | null }[] {
  const section = screen.getByRole("region", { name: "Waiting for review" });
  return within(section)
    .getAllByRole("link")
    .map((link) => ({ name: link.textContent ?? "", href: link.getAttribute("href") }));
}

describe("Today lane tiles", () => {
  it("splits the provider lane into questions to send and waiting on the provider", () => {
    render(<LaneCells counts={COUNTS} reasons={REASONS} role="coder" />);
    expect(tiles()).toEqual([
      { name: "Ready to approve31 due within a day", href: "/queue?lane=approve" },
      { name: "Needs a coder42 due within a day", href: "/queue?lane=coder" },
      { name: "Questions to send21 due within a day", href: "/queue?lane=provider&reason=questions" },
      { name: "Waiting on provider30 due within a day", href: "/queue?lane=provider&reason=waiting_on_provider" },
      { name: "Compliance20 due within a day", href: "/queue?lane=compliance" },
    ]);
  });

  it("sends compliance to its own screen and leaves the tiles unlinked for a viewer", () => {
    const { unmount } = render(<LaneCells counts={COUNTS} reasons={REASONS} role="compliance" />);
    expect(tiles().at(-1)).toEqual({ name: "Compliance20 due within a day", href: "/compliance" });
    unmount();
    render(<LaneCells counts={COUNTS} reasons={REASONS} role="viewer" />);
    const section = screen.getByRole("region", { name: "Waiting for review" });
    expect(within(section).queryAllByRole("link")).toEqual([]);
    expect(within(section).getByText("Questions to send")).toBeInTheDocument();
  });
});

import { render, screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { DayChecksList } from "../DayChecksList";
import { BUSY_DAY, QUIET_DAY } from "./fixtures";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("DayChecksList", () => {
  it("lists each flagged provider day with its flags and opens its first note", () => {
    render(<DayChecksList days={[BUSY_DAY, QUIET_DAY]} />);

    const rows = within(screen.getByRole("list", { name: "Flagged provider days" })).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent(/Elena Varga · .*25 Nov 2026/);
    expect(rows[0]).toHaveTextContent("Time over a plausible dayCloned textHigh-level share");
    expect(rows[0]).toHaveTextContent("1 cloned pair");
    expect(within(rows[0]!).getByRole("link")).toHaveAttribute("href", "/notes/a");
    expect(rows[1]).toHaveTextContent(/Omar Haddad · .*24 Nov 2026/);
    expect(within(rows[1]!).getByRole("link")).toHaveAttribute("href", "/notes/d");
  });
});

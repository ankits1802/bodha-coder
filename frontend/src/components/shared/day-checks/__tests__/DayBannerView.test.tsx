import { fireEvent, render, screen, within } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { DayBannerView } from "../DayBannerView";
import { BUSY_DAY, QUIET_DAY } from "./fixtures";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("DayBannerView", () => {
  it("names every flag of the provider's day with a dot and a word", () => {
    render(<DayBannerView day={BUSY_DAY} noteId="a" />);

    const banner = screen.getByRole("region", { name: "Same provider, same day" });
    expect(within(banner).getByText("Time over a plausible day")).toBeInTheDocument();
    expect(within(banner).getByText("High-level share")).toBeInTheDocument();
    expect(banner).toHaveTextContent("3 notes · 16.7 h documented · 80% at the two highest levels · 1 cloned pair");
  });

  it("shows the summary first and keeps the other notes of the day folded until asked", () => {
    render(<DayBannerView day={BUSY_DAY} noteId="a" />);

    const toggle = screen.getByRole("button", { name: "2 other notes that day" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list", { name: "Other notes that day" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ben Cole" })).not.toBeInTheDocument();
  });

  it("links to the other notes of the day and marks the one cloned from this note", () => {
    render(<DayBannerView day={BUSY_DAY} noteId="a" />);
    fireEvent.click(screen.getByRole("button", { name: "2 other notes that day" }));

    const others = within(screen.getByRole("list", { name: "Other notes that day" })).getAllByRole("listitem");
    expect(others).toHaveLength(2);
    expect(others[0]).toHaveTextContent("Ben Cole99215Cloned text");
    expect(others[1]).toHaveTextContent("Cara Lim99213");
    expect(others[1]).not.toHaveTextContent("Cloned text");
    expect(screen.getByRole("link", { name: "Ben Cole" })).toHaveAttribute("href", "/notes/b");
    expect(screen.queryByRole("link", { name: "Ana Diaz" })).not.toBeInTheDocument();
  });

  it("says the day is clear when nothing is flagged", () => {
    render(<DayBannerView day={QUIET_DAY} noteId="d" />);

    expect(screen.getByText("No same-day issues")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Same provider, same day" })).toHaveTextContent("2 notes · 35 min documented · 0%");
  });
});

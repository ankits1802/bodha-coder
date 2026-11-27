import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { haptic } from "@/lib/haptics";
import { SampleReview } from "../sample/SampleReview";

vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

function findings(): HTMLElement[] {
  return within(screen.getByRole("list", { name: "Suggested changes" })).getAllByRole("listitem");
}

function choice(row: HTMLElement | undefined, name: "Accept" | "Reject"): HTMLElement {
  if (!row) throw new Error("no finding row");
  return within(row).getByRole("button", { name });
}

function claim(): HTMLElement {
  return screen.getByRole("status", { name: "Claim" });
}

function marked(): string[] {
  return [...screen.getByRole("tabpanel").querySelectorAll("mark")].map((mark) => mark.textContent ?? "");
}

describe("SampleReview", () => {
  beforeEach(() => {
    vi.mocked(haptic).mockClear();
  });

  it("offers three sample notes as tabs and opens the first with its first finding in focus", () => {
    render(<SampleReview />);
    const tabs = within(screen.getByRole("tablist", { name: "Sample notes" })).getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      "Billed too highSinus infection",
      "Billed too lowDiabetes follow-up",
      "HCC captureDiabetes with CKD",
    ]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveAccessibleName(/Billed too high/);
    expect(panel).toHaveTextContent("Sample note · Established patient");
    expect(findings()[0]).toHaveAttribute("aria-current", "true");
    expect(marked()).toEqual([
      "Evidence: 10 days of facial pressure and nasal congestion End of evidence",
      "Evidence: Afebrile End of evidence",
      "Evidence: Amoxicillin-clavulanate 875 mg twice daily for 7 days End of evidence",
    ]);
    expect(within(claim()).getByText("99214")).toBeInTheDocument();
    expect(claim()).toHaveTextContent("2 to decide");
    expect(screen.getByRole("link", { name: "Start free trial" })).toHaveAttribute("href", "/sign-up");
  });

  it("switches notes with a click and with the arrow keys", async () => {
    const user = userEvent.setup();
    render(<SampleReview />);
    await user.click(screen.getByRole("tab", { name: /Billed too low/ }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("followed here for primary care since 2019");
    expect(vi.mocked(haptic).mock.calls).toEqual([["select"]]);
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /HCC capture/ })).toHaveFocus();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Urine albumin-to-creatinine ratio 48");
    expect(findings()).toHaveLength(3);
  });

  it("accepts with Y and rejects with N, moving to the next finding and summing up the claim", async () => {
    const user = userEvent.setup();
    render(<SampleReview />);
    await user.click(screen.getByRole("tab", { name: /Billed too high/ }));
    await user.tab();
    expect(screen.getByRole("tabpanel")).toHaveFocus();
    await user.keyboard("y");
    const [visit, diagnosis] = findings();
    expect(choice(visit, "Accept")).toHaveAttribute("aria-pressed", "true");
    expect(choice(diagnosis, "Accept")).toHaveFocus();
    expect(diagnosis).toHaveAttribute("aria-current", "true");
    expect(marked()).toEqual(["Evidence: Acute maxillary sinusitis End of evidence"]);
    expect(claim()).toHaveTextContent("1 to decide");
    await user.keyboard("n");
    expect(choice(diagnosis, "Reject")).toHaveAttribute("aria-pressed", "true");
    expect(within(claim()).getByText("99213")).toBeInTheDocument();
    expect(within(claim()).getByText("J01.90")).toBeInTheDocument();
    expect(within(claim()).queryByText("99214")).toBeNull();
    expect(claim()).toHaveTextContent("Ready to approve");
    expect(marked()).toHaveLength(3);
    expect(marked()[1]).toBe("Evidence: Afebrile End of evidence");
    expect(vi.mocked(haptic)).toHaveBeenLastCalledWith("success");
  });

  it("decides the finding that holds focus, and a second press takes the decision back", async () => {
    const user = userEvent.setup();
    render(<SampleReview />);
    await user.click(screen.getByRole("tab", { name: /Billed too low/ }));
    const [visit, addOn] = findings();
    act(() => choice(addOn, "Reject").focus());
    await user.keyboard("y");
    expect(choice(addOn, "Accept")).toHaveAttribute("aria-pressed", "true");
    expect(choice(visit, "Accept")).toHaveAttribute("aria-pressed", "false");
    expect(within(claim()).getByText("G2211")).toBeInTheDocument();
    expect(choice(visit, "Accept")).toHaveFocus();
    await user.click(choice(addOn, "Accept"));
    expect(choice(addOn, "Accept")).toHaveAttribute("aria-pressed", "false");
    expect(within(claim()).queryByText("G2211")).toBeNull();
    expect(claim()).toHaveTextContent("2 to decide");
  });

  it("ignores Y and N outside the review, and keeps each note's decisions when switching", async () => {
    const user = userEvent.setup();
    render(<SampleReview />);
    const first = screen.getByRole("tab", { name: /Billed too high/ });
    await user.click(first);
    await user.keyboard("y");
    expect(claim()).toHaveTextContent("2 to decide");
    await user.click(choice(findings()[0], "Accept"));
    await user.click(screen.getByRole("tab", { name: /HCC capture/ }));
    expect(claim()).toHaveTextContent("3 to decide");
    await user.click(first);
    expect(choice(findings()[0], "Accept")).toHaveAttribute("aria-pressed", "true");
    expect(within(claim()).getByText("99213")).toBeInTheDocument();
  });

  it("names each decision and its keys for assistive technology", () => {
    render(<SampleReview />);
    const [visit] = findings();
    if (!visit) throw new Error("no finding row");
    expect(within(visit).getByRole("group", { name: "Decision for 99213" })).toBeInTheDocument();
    expect(choice(visit, "Accept")).toHaveAttribute("aria-keyshortcuts", "Y");
    expect(choice(visit, "Reject")).toHaveAttribute("aria-keyshortcuts", "N");
  });
});

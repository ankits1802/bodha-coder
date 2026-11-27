import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FaqList } from "../faq/FaqList";

vi.mock("@/lib/haptics", () => ({ haptic: vi.fn() }));

const ITEMS = [
  { question: "First question?", answer: "First answer." },
  { question: "Second question?", answer: "Second answer." },
];

describe("FaqList", () => {
  it("starts closed, each question a button inside a level 3 heading", () => {
    render(<FaqList items={ITEMS} />);
    expect(screen.getByRole("heading", { level: 3, name: "First question?" })).toBeInTheDocument();
    for (const button of screen.getAllByRole("button")) expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("First answer.")).not.toBeVisible();
  });

  it("opens and closes each answer on its own", async () => {
    const user = userEvent.setup();
    render(<FaqList items={ITEMS} />);
    const first = screen.getByRole("button", { name: "First question?" });
    const second = screen.getByRole("button", { name: "Second question?" });
    await user.click(first);
    expect(first).toHaveAttribute("aria-expanded", "true");
    const answer = screen.getByText("First answer.");
    expect(answer).toBeVisible();
    expect(answer.parentElement).toHaveAttribute("id", first.getAttribute("aria-controls"));
    await user.click(second);
    expect(screen.getByText("Second answer.")).toBeVisible();
    expect(answer).toBeVisible();
    await user.click(first);
    expect(first).toHaveAttribute("aria-expanded", "false");
    expect(answer).not.toBeVisible();
  });

  it("toggles from the keyboard", async () => {
    const user = userEvent.setup();
    render(<FaqList items={ITEMS} />);
    await user.tab();
    expect(screen.getByRole("button", { name: "First question?" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByText("First answer.")).toBeVisible();
    await user.keyboard(" ");
    expect(screen.getByText("First answer.")).not.toBeVisible();
  });
});

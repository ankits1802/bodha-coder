import { fireEvent, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ReviewTopBar } from "../components/ReviewTopBar";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function renderBar(onGo: (noteId: string) => void) {
  return render(
    <ReviewTopBar
      backHref="/queue"
      title="Elena Varga"
      neighbours={{ previous: "note-1", next: null, index: 2, total: 2 }}
      onGo={onGo}
      onOpenPdf={null}
      pdfPending={false}
    />,
  );
}

describe("ReviewTopBar", () => {
  it("names the previous and next buttons with the keys the shortcut list shows", () => {
    const onGo = vi.fn();
    renderBar(onGo);

    const previous = screen.getByRole("button", { name: "Previous note (Shift+K)" });
    const next = screen.getByRole("button", { name: "Next note (Shift+J)" });
    expect(previous).toHaveAttribute("title", "Previous note (Shift+K)");
    expect(next).toBeDisabled();
    fireEvent.click(previous);
    expect(onGo).toHaveBeenCalledWith("note-1");
  });

  it("shows the note's place in the lane", () => {
    renderBar(vi.fn());

    expect(screen.getByText("Note 2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review queue" })).toHaveAttribute("href", "/queue");
  });
});

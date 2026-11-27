import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { returnToCoder } from "@/lib/api/notes";
import { ReturnDialog } from "../ReturnDialog";

vi.mock("@/lib/api/notes", () => ({ returnToCoder: vi.fn() }));

function renderDialog() {
  const onReturned = vi.fn();
  render(<ReturnDialog noteId="note-1" onClose={vi.fn()} onReturned={onReturned} />);
  return { onReturned, user: userEvent.setup() };
}

describe("ReturnDialog", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(returnToCoder).mockResolvedValue({ status: "ready", lane: "coder" });
  });

  it("will not return a note without a reason", async () => {
    const { user } = renderDialog();
    await user.click(screen.getByRole("button", { name: "Return to coder" }));
    expect(returnToCoder).not.toHaveBeenCalled();
    expect(screen.getByText("Choose a reason.")).toBeInTheDocument();
  });

  it("picks the reason with a number key and sends it with the optional note", async () => {
    const { user, onReturned } = renderDialog();
    expect(screen.getByRole("radio", { name: /Level not supported/ })).toHaveFocus();
    await user.keyboard("3");
    expect(screen.getByRole("radio", { name: /Coding error/ })).toBeChecked();
    await user.click(screen.getByRole("textbox", { name: /Note/ }));
    await user.keyboard("Modifier 25 is missing{Enter}");
    expect(returnToCoder).toHaveBeenCalledWith("note-1", { reason: "coding_error", note: "Modifier 25 is missing" });
    expect(onReturned).toHaveBeenCalledWith({ status: "ready", lane: "coder" });
  });

  it("needs a note before Other is sent", async () => {
    const { user } = renderDialog();
    await user.keyboard("6{Enter}");
    expect(returnToCoder).not.toHaveBeenCalled();
    expect(screen.getByText("Write a short note for Other.")).toBeInTheDocument();
  });
});

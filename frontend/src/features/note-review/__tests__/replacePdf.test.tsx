import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { replaceNoteDocument } from "@/lib/api/notes";
import { ReplacePdfButton } from "../components/ReplacePdfButton";
import { canReplacePdf } from "../replacePdf";

vi.mock("@/lib/api/notes", () => ({ replaceNoteDocument: vi.fn() }));

describe("canReplacePdf", () => {
  it("lets uploaders replace the PDF until the note is exported, but not while it is being read", () => {
    expect(canReplacePdf("coder", "ready")).toBe(true);
    expect(canReplacePdf("admin", "approved")).toBe(true);
    expect(canReplacePdf("admin", "failed")).toBe(true);
    expect(canReplacePdf("admin", "exported")).toBe(false);
    expect(canReplacePdf("admin", "reading")).toBe(false);
    expect(canReplacePdf("biller", "ready")).toBe(false);
    expect(canReplacePdf("cdi", "ready")).toBe(false);
  });
});

describe("ReplacePdfButton", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("asks before replacing the PDF with the chosen file", async () => {
    vi.mocked(replaceNoteDocument).mockResolvedValue({ status: "queued" });
    const onReplaced = vi.fn();
    render(<ReplacePdfButton noteId="note-1" onReplaced={onReplaced} />);
    const amended = new File(["%PDF-1.7 amended"], "amended.pdf", { type: "application/pdf" });

    fireEvent.change(screen.getByLabelText("Choose the amended PDF"), { target: { files: [amended] } });
    expect(await screen.findByText("Replace the PDF with amended.pdf?")).toBeInTheDocument();
    expect(replaceNoteDocument).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Replace" }));

    await waitFor(() => expect(onReplaced).toHaveBeenCalledTimes(1));
    expect(replaceNoteDocument).toHaveBeenCalledWith("note-1", amended);
  });

  it("ignores a file that is not a PDF", () => {
    render(<ReplacePdfButton noteId="note-1" onReplaced={vi.fn()} />);
    const text = new File(["note"], "note.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Choose the amended PDF"), { target: { files: [text] } });
    expect(screen.queryByText(/Replace the PDF with/)).not.toBeInTheDocument();
  });
});

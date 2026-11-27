import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { restoreNote } from "@/lib/api/notes";
import type { NoteChangeRecord, NoteHeader } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { HistoryChanges } from "../components/HistoryChanges";
import { StatusBanner } from "../components/StatusBanner";

vi.mock("@/lib/api/notes", () => ({ restoreNote: vi.fn() }));

const VOIDED_AT = "2026-11-28T15:30:00Z";
const NOTE = {
  id: "note-1",
  status: "voided",
  flag_reason: null,
  voided: { at: VOIDED_AT, by: "Priya Nair", reason: "Uploaded to the wrong provider", was: "queued" },
} as unknown as NoteHeader;

function banner(canRestore: boolean, onRestored = vi.fn()) {
  return render(
    <StatusBanner note={NOTE} reason={null} onRetry={null} onReopen={null} retryPending={false} canRestore={canRestore} onRestored={onRestored} />,
  );
}

describe("a voided note", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("says who voided it, when and why", () => {
    banner(false);
    expect(screen.getByText(`Voided by Priya Nair, ${formatDateTime(VOIDED_AT)}: Uploaded to the wrong provider`)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Restore" })).not.toBeInTheDocument();
  });

  it("lets an admin restore it once a reason is given", async () => {
    vi.mocked(restoreNote).mockResolvedValue({ status: "queued" });
    const onRestored = vi.fn();
    banner(true, onRestored);
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    const form = screen.getByRole("heading", { name: "Restore this note?" }).closest("dialog")?.querySelector("form");
    if (!form) throw new Error("restore dialog not open");
    fireEvent.submit(form);
    expect(await screen.findByText("Give the reason")).toBeInTheDocument();
    expect(restoreNote).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("textbox", { name: "Reason" }), { target: { value: "Voided by mistake" } });
    fireEvent.submit(form);
    await waitFor(() => expect(restoreNote).toHaveBeenCalledWith("note-1", "Voided by mistake"));
    await waitFor(() => expect(onRestored).toHaveBeenCalledTimes(1));
  });
});

describe("HistoryChanges", () => {
  it("shows each change with its value before and after, why and by whom", () => {
    const changes: NoteChangeRecord[] = [
      { field: "status", old: "queued", new: "voided", reason: "Uploaded to the wrong provider", by: "Priya Nair", at: VOIDED_AT },
      { field: "payer", old: null, new: "Medicare Part B", reason: null, by: null, at: VOIDED_AT },
    ];
    render(<HistoryChanges changes={changes} />);
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Waiting to be read → Voided")).toBeInTheDocument();
    expect(screen.getByText("Uploaded to the wrong provider · by Priya Nair")).toBeInTheDocument();
    expect(screen.getByText("Not set → Medicare Part B")).toBeInTheDocument();
    expect(screen.getByText("by Bodha")).toBeInTheDocument();
  });
});

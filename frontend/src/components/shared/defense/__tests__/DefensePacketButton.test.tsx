import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { downloadDefensePacket } from "@/lib/api/defensibility";
import { ApiError } from "@/lib/api/errors";
import { saveFile } from "@/lib/download";
import { DefensePacketButton } from "../DefensePacketButton";

vi.mock("@/lib/api/defensibility", () => ({ downloadDefensePacket: vi.fn() }));
vi.mock("@/lib/download", () => ({ saveFile: vi.fn() }));

const PDF = new Blob(["%PDF-1.4"], { type: "application/pdf" });

describe("DefensePacketButton", () => {
  beforeEach(() => {
    vi.mocked(saveFile).mockReset();
  });

  it("saves the packet under the name the server gives", async () => {
    vi.mocked(downloadDefensePacket).mockResolvedValue({ blob: PDF, fileName: "bodha-defense-packet-20261125-abcd1234.pdf" });
    render(<DefensePacketButton noteId="note-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Download the audit defense packet as a PDF" }));

    await vi.waitFor(() => expect(saveFile).toHaveBeenCalledWith(PDF, "bodha-defense-packet-20261125-abcd1234.pdf"));
    expect(downloadDefensePacket).toHaveBeenCalledWith("note-1");
  });

  it("shows why the packet could not be downloaded", async () => {
    vi.mocked(downloadDefensePacket).mockRejectedValue(new ApiError(404, "not_found", "note not found"));
    render(<DefensePacketButton noteId="note-2" />);

    fireEvent.click(screen.getByRole("button", { name: "Download the audit defense packet as a PDF" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Note not found");
    expect(saveFile).not.toHaveBeenCalled();
  });
});

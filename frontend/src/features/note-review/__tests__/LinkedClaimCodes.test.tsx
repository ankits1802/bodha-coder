import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/errors";
import { getClaimPointers, saveLinePointers } from "@/lib/api/pointers";
import type { ClaimPointers } from "@/lib/api/types";
import { LinkedClaimCodes } from "../components/LinkedClaimCodes";

vi.mock("@/lib/api/pointers", () => ({ getClaimPointers: vi.fn(), saveLinePointers: vi.fn() }));

const CLAIM = ["99214", "96127 ×2", "E11.65", "N18.30"];
const DIAGNOSES = [
  { code: "E11.65", letter: "A" },
  { code: "N18.30", letter: "B" },
];
const SHOWN: ClaimPointers = {
  diagnoses: DIAGNOSES,
  lines: [
    { code: "99214", label: "99214", pointers: ["E11.65", "N18.30"], stored: false },
    { code: "96127", label: "96127 ×2", pointers: ["E11.65", "N18.30"], stored: false },
  ],
};
const SAVED: ClaimPointers = {
  diagnoses: DIAGNOSES,
  lines: [SHOWN.lines[0]!, { code: "96127", label: "96127 ×2", pointers: ["N18.30"], stored: true }],
};

describe("LinkedClaimCodes", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("saves the diagnoses chosen for a line and shows the new pointers", async () => {
    vi.mocked(getClaimPointers).mockResolvedValue(SHOWN);
    vi.mocked(saveLinePointers).mockResolvedValue(SAVED);
    render(<LinkedClaimCodes noteId="note-1" claim={CLAIM} estimate={null} editable />);

    fireEvent.click(await screen.findByRole("button", { name: "96127 ×2 AB, diagnoses E11.65, N18.30" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "A E11.65 1st" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("button", { name: "96127 ×2 B, diagnoses N18.30" })).toBeInTheDocument();
    expect(saveLinePointers).toHaveBeenCalledWith("note-1", "96127", ["N18.30"]);
    await waitFor(() => expect(screen.queryByRole("button", { name: "Save" })).toBeNull());
  });

  it("keeps the editor open with the reason when saving fails", async () => {
    vi.mocked(getClaimPointers).mockResolvedValue(SHOWN);
    vi.mocked(saveLinePointers).mockRejectedValue(new ApiError(422, "invalid", "N18.30 is not a diagnosis on the claim"));
    render(<LinkedClaimCodes noteId="note-1" claim={CLAIM} estimate={null} editable />);

    fireEvent.click(await screen.findByRole("button", { name: "99214 AB, diagnoses E11.65, N18.30" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("N18.30 is not a diagnosis on the claim");
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("shows plain codes to someone who cannot change the claim", async () => {
    vi.mocked(getClaimPointers).mockResolvedValue(SHOWN);
    render(<LinkedClaimCodes noteId="note-1" claim={CLAIM} estimate={null} editable={false} />);

    expect(await screen.findAllByText("AB")).toHaveLength(2);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("says when the diagnosis links could not be loaded", async () => {
    vi.mocked(getClaimPointers).mockRejectedValue(new Error("offline"));
    render(<LinkedClaimCodes noteId="note-1" claim={CLAIM} estimate={null} editable />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Diagnosis links unavailable");
    expect(screen.getByText("99214")).toBeInTheDocument();
  });
});

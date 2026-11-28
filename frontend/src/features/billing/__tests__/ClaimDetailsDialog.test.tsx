import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getClaimDetails, saveClaimDetails } from "@/lib/api/claims";
import { getPayers, setNotePayer } from "@/lib/api/notes";
import type { ClaimDetailsView } from "@/lib/api/types";
import { ClaimDetailsDialog } from "../components/ClaimDetailsDialog";
import { claimRow } from "./claimFixtures";

vi.mock("@/lib/api/claims", () => ({ getClaimDetails: vi.fn(), saveClaimDetails: vi.fn() }));
vi.mock("@/lib/api/notes", () => ({ getPayers: vi.fn(), setNotePayer: vi.fn() }));

const FROM_NOTE: ClaimDetailsView = {
  details: null,
  suggested: { source: "note", patient_name: "Marisol Reyes", patient_birth_date: "1959-03-12", patient_sex: "F" },
};
const ROW = claimRow("note-1", { status: "missing", at: null, reasons: [], missing: ["payer", "details"] });

function type(label: string | RegExp, value: string): void {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("claim details", () => {
  beforeEach(() => {
    vi.mocked(getClaimDetails).mockResolvedValue(FROM_NOTE);
    vi.mocked(getPayers).mockResolvedValue([{ id: "payer-1", name: "Medicare Part B", plan_type: "medicare" }]);
    vi.mocked(setNotePayer).mockResolvedValue({ payer: "payer-1" });
    vi.mocked(saveClaimDetails).mockResolvedValue({ details: null, suggested: null });
  });

  afterEach(() => {
    vi.mocked(saveClaimDetails).mockReset();
    vi.mocked(setNotePayer).mockReset();
  });

  it("shows the name read from the note and leaves the name fields for a person to fill", async () => {
    render(<ClaimDetailsDialog row={ROW} onClose={vi.fn()} onSaved={vi.fn()} />);
    expect(await screen.findByText("Name on the note: Marisol Reyes")).toBeInTheDocument();
    expect(screen.getByLabelText("Patient last name")).toHaveValue("");
    expect(screen.getByLabelText("Patient first name")).toHaveValue("");
    expect(screen.getByRole("radio", { name: "Female" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText("Missing: Payer, Patient and subscriber")).toBeInTheDocument();
  });

  it("asks for the subscriber only when the patient is not the subscriber", async () => {
    render(<ClaimDetailsDialog row={ROW} onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByLabelText("Patient last name");
    expect(screen.queryByLabelText("Subscriber last name")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Spouse" }));
    expect(screen.getByLabelText("Subscriber last name")).toBeInTheDocument();
    expect(screen.getByLabelText("Subscriber first name")).toBeInTheDocument();
  });

  it("saves the payer on the note and the confirmed details", async () => {
    const onSaved = vi.fn();
    render(<ClaimDetailsDialog row={ROW} onClose={vi.fn()} onSaved={onSaved} />);
    await screen.findByLabelText("Patient last name");
    fireEvent.click(screen.getByRole("combobox", { name: "Payer" }));
    fireEvent.click(screen.getByRole("option", { name: "Medicare Part B" }));
    type("Patient last name", "Reyes");
    type("Patient first name", "Marisol");
    type("Street address", "9 Elm St");
    type("City", "Springfield");
    type("State", "il");
    type("ZIP code", "62704");
    type("Member ID", "xyz123456789");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveClaimDetails).toHaveBeenCalledTimes(1));
    expect(setNotePayer).toHaveBeenCalledWith("note-1", "payer-1");
    expect(saveClaimDetails).toHaveBeenCalledWith("note-1", {
      patient_last: "Reyes",
      patient_first: "Marisol",
      patient_birth_date: "1959-03-12",
      patient_sex: "F",
      street: "9 Elm St",
      street_2: null,
      city: "Springfield",
      state: "IL",
      zip_code: "62704",
      relationship: "18",
      member_id: "XYZ123456789",
      group_number: null,
      subscriber_last: null,
      subscriber_first: null,
    });
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
  });

  it("does not save until the required fields are filled", async () => {
    render(<ClaimDetailsDialog row={ROW} onClose={vi.fn()} onSaved={vi.fn()} />);
    await screen.findByLabelText("Patient last name");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findAllByText("Fill this in")).not.toHaveLength(0);
    expect(saveClaimDetails).not.toHaveBeenCalled();
  });
});

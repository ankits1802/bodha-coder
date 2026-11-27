import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ClaimDiagnosis, PointerLine } from "@/lib/api/types";
import { PointerEditor, toggledPointer } from "../components/PointerEditor";

const DIAGNOSES: ClaimDiagnosis[] = [
  { code: "E11.65", letter: "A" },
  { code: "N18.30", letter: "B" },
  { code: "I12.9", letter: "C" },
  { code: "R20.2", letter: "D" },
  { code: "Z79.4", letter: "E" },
];
const LINKED: PointerLine = { code: "96127", label: "96127 ×2", pointers: ["N18.30"], stored: true };

function renderEditor(line: PointerLine, onSave = vi.fn()) {
  render(<PointerEditor line={line} diagnoses={DIAGNOSES} pending={false} error={null} onSave={onSave} onClose={vi.fn()} />);
  return onSave;
}

describe("toggledPointer", () => {
  it("adds a diagnosis at the end, removes a chosen one and stops at four", () => {
    expect(toggledPointer(["I10"], "E11.65")).toEqual(["I10", "E11.65"]);
    expect(toggledPointer(["I10", "E11.65"], "I10")).toEqual(["E11.65"]);
    expect(toggledPointer(["A00", "B00", "C00", "D00"], "E00")).toEqual(["A00", "B00", "C00", "D00"]);
  });
});

describe("PointerEditor", () => {
  it("keeps the order the coder chooses in and saves it", () => {
    const onSave = renderEditor(LINKED);
    expect(screen.getByRole("checkbox", { name: "B N18.30 1st" })).toBeChecked();
    expect(screen.getByText("1 of 4")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "C I12.9" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "A E11.65" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "D R20.2" }));
    expect(screen.getByRole("checkbox", { name: "E Z79.4" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "B N18.30 1st" }));

    expect(screen.getByRole("checkbox", { name: "C I12.9 1st" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "A E11.65 2nd" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "E Z79.4" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith(["I12.9", "E11.65", "R20.2"]);
  });

  it("is used from the keyboard", async () => {
    const user = userEvent.setup();
    const onSave = renderEditor(LINKED);

    screen.getByRole("checkbox", { name: "A E11.65" }).focus();
    await user.tab();
    expect(screen.getByRole("checkbox", { name: "B N18.30 1st" })).toHaveFocus();
    await user.tab();
    await user.keyboard(" ");

    expect(screen.getByRole("checkbox", { name: "C I12.9 2nd" })).toBeChecked();
    screen.getByRole("button", { name: "Save" }).focus();
    await user.keyboard("{Enter}");
    expect(onSave).toHaveBeenCalledWith(["N18.30", "I12.9"]);
  });

  it("returns a linked line to the default and cannot save an empty choice", () => {
    const onSave = renderEditor(LINKED);
    fireEvent.click(screen.getByRole("checkbox", { name: "B N18.30 1st" }));
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Use default" }));
    expect(onSave).toHaveBeenCalledWith([]);
  });

  it("offers no default for a line that already follows it", () => {
    renderEditor({ code: "99214", label: "99214", pointers: ["E11.65", "N18.30", "I12.9", "R20.2"], stored: false });

    expect(screen.queryByRole("button", { name: "Use default" })).toBeNull();
    expect(screen.getByRole("checkbox", { name: "E Z79.4" })).toBeDisabled();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SignatureFields } from "../SignatureFields";
import { SignaturePad } from "../SignaturePad";
import type { PadStroke } from "../strokes";
import { useSignatureEntry } from "../useSignatureEntry";

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

function Pad({ onChange }: { onChange: (strokes: PadStroke[]) => void }) {
  const [strokes, setStrokes] = useState<PadStroke[]>([]);
  return (
    <SignaturePad
      strokes={strokes}
      onChange={(next) => {
        setStrokes(next);
        onChange(next);
      }}
    />
  );
}

function Fields() {
  const state = useSignatureEntry("Cora Coder");
  return (
    <>
      <SignatureFields state={state} />
      <output>{state.ready ? "ready" : "not ready"}</output>
    </>
  );
}

function stroke(pad: HTMLElement, pointerType: string, pointerId: number): void {
  fireEvent.pointerDown(pad, { pointerId, pointerType, button: 0, clientX: 10, clientY: 10 });
  fireEvent.pointerMove(pad, { pointerId, pointerType, clientX: 60, clientY: 30 });
  fireEvent.pointerUp(pad, { pointerId, pointerType, clientX: 90, clientY: 40 });
}

describe("signature pad", () => {
  it("records one stroke per touch or pen and offers undo and clear only when signed", () => {
    const onChange = vi.fn();
    render(<Pad onChange={onChange} />);
    const pad = screen.getByRole("img", { name: "Signature pad, empty" });
    expect(screen.getByRole("button", { name: "Undo" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Clear" })).toBeDisabled();

    stroke(pad, "touch", 1);
    stroke(pad, "pen", 2);

    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ pointer: "touch" }),
      expect.objectContaining({ pointer: "pen" }),
    ]);
    expect(screen.getByRole("img", { name: "Signature pad, signed" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(onChange).toHaveBeenLastCalledWith([expect.objectContaining({ pointer: "touch" })]);
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
    expect(screen.getByRole("img", { name: "Signature pad, empty" })).toBeInTheDocument();
  });

  it("ignores a right click and a second finger while a stroke is drawn", () => {
    const onChange = vi.fn();
    render(<Pad onChange={onChange} />);
    const pad = screen.getByRole("img", { name: "Signature pad, empty" });

    fireEvent.pointerDown(pad, { pointerId: 1, pointerType: "mouse", button: 2, clientX: 5, clientY: 5 });
    fireEvent.pointerUp(pad, { pointerId: 1, pointerType: "mouse", clientX: 5, clientY: 5 });
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.pointerDown(pad, { pointerId: 3, pointerType: "touch", button: 0, clientX: 5, clientY: 5 });
    fireEvent.pointerDown(pad, { pointerId: 4, pointerType: "touch", button: 0, clientX: 50, clientY: 50 });
    fireEvent.pointerUp(pad, { pointerId: 4, pointerType: "touch", clientX: 50, clientY: 50 });
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.pointerUp(pad, { pointerId: 3, pointerType: "touch", clientX: 40, clientY: 30 });
    expect(onChange).toHaveBeenCalledTimes(1);
  });
});

describe("signing without a pointer", () => {
  it("lets a keyboard user switch to a typed signature of their full name", async () => {
    const user = userEvent.setup();
    render(<Fields />);
    expect(screen.getByRole("status")).toHaveTextContent("not ready");

    await user.tab();
    expect(screen.getByRole("radio", { name: "Draw" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("radio", { name: "Type" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("img", { name: "Signature: Cora Coder" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/^ready$/);

    await user.tab();
    const name = screen.getByRole("textbox", { name: "Full name" });
    expect(name).toHaveFocus();
    await user.clear(name);
    expect(screen.getByRole("status")).toHaveTextContent("not ready");
    await user.keyboard("Cora M. Coder");

    expect(name).toHaveValue("Cora M. Coder");
    expect(screen.getByRole("img", { name: "Signature: Cora M. Coder" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/^ready$/);
  });
});

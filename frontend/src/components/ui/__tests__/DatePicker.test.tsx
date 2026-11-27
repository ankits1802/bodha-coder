import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DateHarness, TODAY } from "./harness";

describe("DatePicker field", () => {
  it("shows the day the way the rest of the app writes it", () => {
    render(<DateHarness />);
    expect(screen.getByRole("textbox", { name: "Day" })).toHaveValue("27 Nov 2026");
  });

  it("accepts a typed day and writes it back in the app's format", () => {
    const onChange = vi.fn();
    render(<DateHarness onChange={onChange} />);
    const field = screen.getByRole("textbox", { name: "Day" });
    fireEvent.change(field, { target: { value: "3/2/2026" } });
    expect(onChange).toHaveBeenLastCalledWith("2026-02-03");
    fireEvent.blur(field);
    expect(field).toHaveValue("3 Feb 2026");
    expect(field).not.toHaveAttribute("aria-invalid");
  });

  it("marks a typed day that does not exist or is out of range, without passing it on", () => {
    const onChange = vi.fn();
    render(<DateHarness max={TODAY} onChange={onChange} />);
    const field = screen.getByRole("textbox", { name: "Day" });
    fireEvent.change(field, { target: { value: "31 Feb 2026" } });
    fireEvent.blur(field);
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveValue("31 Feb 2026");
    fireEvent.change(field, { target: { value: "28 Nov 2026" } });
    fireEvent.blur(field);
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("passes on null when the field is cleared", () => {
    const onChange = vi.fn();
    render(<DateHarness onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Day" }), { target: { value: "" } });
    expect(onChange).toHaveBeenCalledWith(null);
  });
});

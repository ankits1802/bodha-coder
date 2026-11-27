import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { DateRange, type DateRangeValue } from "../DateRange";

function Harness({ onChange }: { onChange: (range: DateRangeValue) => void }) {
  const [range, setRange] = useState<DateRangeValue>({ start: "2026-11-10", end: "2026-11-20" });
  const change = (next: DateRangeValue) => {
    setRange(next);
    onChange(next);
  };
  return <DateRange start={range.start} end={range.end} labels={{ start: "From", end: "To" }} today="2026-11-27" onChange={change} />;
}

describe("DateRange", () => {
  it("labels both fields and both calendar buttons", () => {
    render(<Harness onChange={() => undefined} />);
    expect(screen.getByRole("textbox", { name: "From" })).toHaveValue("10 Nov 2026");
    expect(screen.getByRole("textbox", { name: "To" })).toHaveValue("20 Nov 2026");
    expect(screen.getByRole("button", { name: "Choose date From" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose date To" })).toBeInTheDocument();
  });

  it("offers no start after the end and no end before the start", () => {
    render(<Harness onChange={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Choose date From" }));
    expect(screen.getByRole("button", { name: "Friday 20 November 2026" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Saturday 21 November 2026" })).toBeDisabled();
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Choose date To" }));
    expect(screen.getByRole("button", { name: "Tuesday 10 November 2026" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Monday 9 November 2026" })).toBeDisabled();
  });

  it("refuses a typed end before the start and passes on a valid one", () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    const end = screen.getByRole("textbox", { name: "To" });
    fireEvent.change(end, { target: { value: "5 Nov 2026" } });
    fireEvent.blur(end);
    expect(end).toHaveAttribute("aria-invalid", "true");
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(end, { target: { value: "24 Nov 2026" } });
    expect(onChange).toHaveBeenCalledWith({ start: "2026-11-10", end: "2026-11-24" });
  });
});

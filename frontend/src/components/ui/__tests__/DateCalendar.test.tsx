import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DateHarness, TODAY, openCalendar, press } from "./harness";

describe("DatePicker calendar", () => {
  it("opens on the chosen day, marks today and labels every day in full", () => {
    render(<DateHarness initial="2026-11-25" />);
    const dialog = openCalendar();
    expect(dialog).toHaveAccessibleName("November 2026");
    const chosen = screen.getByRole("button", { name: "Wednesday 25 November 2026" });
    expect(chosen).toHaveFocus();
    expect(chosen.closest("td")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("button", { name: "Friday 27 November 2026" })).toHaveAttribute("aria-current", "date");
  });

  it("moves by day, week, month and year, and to the ends of the week", () => {
    render(<DateHarness />);
    const dialog = openCalendar();
    press("ArrowRight");
    expect(screen.getByRole("button", { name: "Saturday 28 November 2026" })).toHaveFocus();
    press("ArrowDown");
    expect(screen.getByRole("button", { name: "Saturday 5 December 2026" })).toHaveFocus();
    expect(dialog).toHaveAccessibleName("December 2026");
    press("PageUp");
    expect(screen.getByRole("button", { name: "Thursday 5 November 2026" })).toHaveFocus();
    press("PageDown", true);
    expect(screen.getByRole("button", { name: "Friday 5 November 2027" })).toHaveFocus();
    press("Home");
    expect(screen.getByRole("button", { name: "Monday 1 November 2027" })).toHaveFocus();
    press("End");
    expect(screen.getByRole("button", { name: "Sunday 7 November 2027" })).toHaveFocus();
  });

  it("picks a clicked day, closes and returns focus to the calendar button", () => {
    const onChange = vi.fn();
    render(<DateHarness onChange={onChange} />);
    openCalendar();
    fireEvent.click(screen.getByRole("button", { name: "Wednesday 25 November 2026" }));
    expect(onChange).toHaveBeenCalledWith("2026-11-25");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Day" })).toHaveValue("25 Nov 2026");
    expect(screen.getByRole("button", { name: "Choose day" })).toHaveFocus();
  });

  it("closes on Escape and returns focus", () => {
    render(<DateHarness />);
    openCalendar();
    press("Escape");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose day" })).toHaveFocus();
  });

  it("keeps days outside the range out of reach", () => {
    render(<DateHarness min="2026-11-10" max={TODAY} />);
    openCalendar();
    expect(screen.getByRole("button", { name: "Saturday 28 November 2026" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Monday 9 November 2026" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next month" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous month" })).toBeDisabled();
    press("ArrowRight");
    expect(screen.getByRole("button", { name: "Friday 27 November 2026" })).toHaveFocus();
  });

  it("picks today from the Today button", () => {
    const onChange = vi.fn();
    render(<DateHarness initial="2026-11-02" onChange={onChange} />);
    openCalendar();
    fireEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(onChange).toHaveBeenCalledWith(TODAY);
  });

  it("jumps to a month and a year from the header", () => {
    render(<DateHarness />);
    const dialog = openCalendar();
    fireEvent.click(screen.getByRole("combobox", { name: "Month" }));
    fireEvent.click(screen.getByRole("option", { name: "March" }));
    expect(dialog).toHaveAccessibleName("March 2026");
    expect(screen.getByRole("button", { name: "Friday 27 March 2026" })).toHaveAttribute("tabindex", "0");
    fireEvent.click(screen.getByRole("combobox", { name: "Year" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Search" }), { target: { value: "2024" } });
    fireEvent.click(screen.getByRole("option", { name: "2024" }));
    expect(dialog).toHaveAccessibleName("March 2024");
    expect(screen.getByRole("button", { name: "Wednesday 27 March 2024" })).toHaveAttribute("tabindex", "0");
  });

  it("closes only the month list on Escape inside the header", () => {
    render(<DateHarness />);
    openCalendar();
    const month = screen.getByRole("combobox", { name: "Month" });
    fireEvent.click(month);
    fireEvent.keyDown(month, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

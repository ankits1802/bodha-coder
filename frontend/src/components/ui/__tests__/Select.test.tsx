import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SelectHarness, activeLabel } from "./harness";

describe("Select with the mouse", () => {
  it("shows the chosen label and lists every option with the chosen one selected", () => {
    render(<SelectHarness initial="u1" />);
    const box = screen.getByRole("combobox", { name: "Person" });
    expect(box).toHaveTextContent("Priya Nair");
    expect(box).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(box);
    const list = screen.getByRole("listbox", { name: "Person" });
    expect(box).toHaveAttribute("aria-expanded", "true");
    expect(box).toHaveAttribute("aria-controls", list.id);
    expect(within(list).getAllByRole("option").map((option) => option.textContent)).toEqual(["Anyone", "Priya Nair", "Omar Haddad", "Sam Okafor"]);
    expect(screen.getByRole("option", { name: "Priya Nair" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("option", { name: "Anyone" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("option", { name: "Omar Haddad" })).toHaveAttribute("aria-disabled", "true");
  });

  it("chooses a clicked option, closes and gives focus back, but ignores a disabled one", () => {
    const onChange = vi.fn();
    render(<SelectHarness onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    fireEvent.click(box);
    fireEvent.click(screen.getByRole("option", { name: "Omar Haddad" }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("option", { name: "Sam Okafor" }));
    expect(onChange).toHaveBeenCalledWith("u3");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(box).toHaveTextContent("Sam Okafor");
    expect(box).toHaveFocus();
  });

  it("closes on a click outside without changing the value", () => {
    const onChange = vi.fn();
    render(<SelectHarness onChange={onChange} />);
    fireEvent.click(screen.getByRole("combobox", { name: "Person" }));
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("Select with the keyboard", () => {
  it("opens on the current option and moves over enabled options only", () => {
    const onChange = vi.fn();
    render(<SelectHarness onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(activeLabel(box)).toBe("Anyone");
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(activeLabel(box)).toBe("Priya Nair");
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(activeLabel(box)).toBe("Sam Okafor");
    fireEvent.keyDown(box, { key: "Home" });
    expect(activeLabel(box)).toBe("Anyone");
    fireEvent.keyDown(box, { key: "ArrowUp" });
    expect(activeLabel(box)).toBe("Anyone");
    fireEvent.keyDown(box, { key: "End" });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("u3");
    expect(box).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on Escape and keeps the value", () => {
    const onChange = vi.fn();
    render(<SelectHarness initial="u1" onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    fireEvent.keyDown(box, { key: "Enter" });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
    expect(box).toHaveTextContent("Priya Nair");
    expect(box).toHaveFocus();
  });

  it("chooses the highlighted option on Tab, like a native select", () => {
    const onChange = vi.fn();
    render(<SelectHarness onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    fireEvent.keyDown(box, { key: " " });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "Tab" });
    expect(onChange).toHaveBeenCalledWith("u1");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("jumps to the first option starting with a typed letter", () => {
    const onChange = vi.fn();
    render(<SelectHarness onChange={onChange} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    fireEvent.keyDown(box, { key: "s" });
    expect(box).toHaveAttribute("aria-expanded", "true");
    expect(activeLabel(box)).toBe("Sam Okafor");
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("u3");
  });
});

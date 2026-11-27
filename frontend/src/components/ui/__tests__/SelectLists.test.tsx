import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Field } from "../Field";
import { Select, type SelectOption } from "../Select";
import { PEOPLE, SelectHarness, ZONES } from "./harness";

describe("Select for long lists, groups and forms", () => {
  it("offers a search box above twelve options and filters by label", () => {
    const onChange = vi.fn();
    render(<SelectHarness options={ZONES} initial="Central" onChange={onChange} />);
    fireEvent.click(screen.getByRole("combobox", { name: "Person" }));
    const search = screen.getByRole("combobox", { name: "Search" });
    expect(search).toHaveFocus();
    fireEvent.change(search, { target: { value: "pac" } });
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual(["Pacific"]);
    fireEvent.keyDown(search, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("Pacific");
  });

  it("says when a search matches nothing", () => {
    render(<SelectHarness options={ZONES} initial="Central" />);
    fireEvent.click(screen.getByRole("combobox", { name: "Person" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Search" }), { target: { value: "zz" } });
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByRole("status")).toHaveTextContent("No matches");
  });

  it("shows no search box for a short list", () => {
    render(<SelectHarness />);
    fireEvent.click(screen.getByRole("combobox", { name: "Person" }));
    expect(screen.queryByRole("combobox", { name: "Search" })).not.toBeInTheDocument();
  });

  it("names option groups", () => {
    const grouped: SelectOption[] = [
      { value: "a", label: "Priya Nair", group: "Recent" },
      { value: "b", label: "Sam Okafor", group: "Everyone" },
    ];
    render(<SelectHarness options={grouped} initial="a" />);
    fireEvent.click(screen.getByRole("combobox", { name: "Person" }));
    expect(within(screen.getByRole("group", { name: "Recent" })).getByRole("option")).toHaveTextContent("Priya Nair");
    expect(within(screen.getByRole("group", { name: "Everyone" })).getByRole("option")).toHaveTextContent("Sam Okafor");
  });

  it("takes its label, error and description from Field and submits its value by name", () => {
    render(
      <form aria-label="Invite">
        <Field label="Role" error="Choose a role">
          {(control) => <Select {...control} name="role" value="coder" options={[{ value: "coder", label: "Coder" }]} onChange={() => undefined} />}
        </Field>
      </form>,
    );
    const box = screen.getByRole("combobox", { name: "Role" });
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription("Choose a role");
    expect(new FormData(screen.getByRole("form", { name: "Invite" }) as HTMLFormElement).get("role")).toBe("coder");
  });

  it("does not open when disabled", () => {
    render(<Select label="Person" value="" options={PEOPLE} disabled onChange={() => undefined} />);
    const box = screen.getByRole("combobox", { name: "Person" });
    expect(box).toBeDisabled();
    fireEvent.click(box);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});

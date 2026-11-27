import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { DatePicker } from "../DatePicker";
import { Select, type SelectOption } from "../Select";

export const TODAY = "2026-11-27";

export const PEOPLE: SelectOption[] = [
  { value: "", label: "Anyone" },
  { value: "u1", label: "Priya Nair" },
  { value: "u2", label: "Omar Haddad", disabled: true },
  { value: "u3", label: "Sam Okafor" },
];

export const ZONES: SelectOption[] = [
  "Aleutian",
  "Alaska",
  "Arizona",
  "Atlantic",
  "Central",
  "Chamorro",
  "Eastern",
  "Hawaii",
  "Mountain",
  "Pacific",
  "Puerto Rico",
  "Samoa",
  "UTC",
].map((label) => ({ value: label, label }));

interface SelectHarnessProps {
  options?: SelectOption[];
  initial?: string;
  onChange?: (value: string) => void;
}

export function SelectHarness({ options = PEOPLE, initial = "", onChange = () => undefined }: SelectHarnessProps) {
  const [value, setValue] = useState(initial);
  const choose = (next: string) => {
    setValue(next);
    onChange(next);
  };
  return <Select label="Person" value={value} options={options} onChange={choose} />;
}

export function activeLabel(box: HTMLElement): string | null | undefined {
  return document.getElementById(box.getAttribute("aria-activedescendant") ?? "")?.textContent;
}

interface DateHarnessProps {
  initial?: string | null;
  min?: string;
  max?: string;
  onChange?: (value: string | null) => void;
}

export function DateHarness({ initial = TODAY, min, max, onChange = () => undefined }: DateHarnessProps) {
  const [value, setValue] = useState<string | null>(initial);
  const change = (next: string | null) => {
    setValue(next);
    onChange(next);
  };
  return <DatePicker label="Day" value={value} min={min} max={max} today={TODAY} onChange={change} />;
}

export function openCalendar(): HTMLElement {
  fireEvent.click(screen.getByRole("button", { name: "Choose day" }));
  return screen.getByRole("dialog");
}

export function press(key: string, shiftKey = false): void {
  fireEvent.keyDown(document.activeElement as HTMLElement, { key, shiftKey });
}

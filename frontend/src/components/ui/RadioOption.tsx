import type { ReactNode } from "react";

interface RadioOptionProps {
  name: string;
  value: string;
  checked: boolean;
  onSelect: () => void;
  children: ReactNode;
}

export const OPTION_CARD =
  "has-checked:shadow-option-on has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus";

const OPTION = `flex min-h-12 cursor-pointer items-center gap-3 rounded-field px-3.5 text-body text-label shadow-option hover:bg-row-hover ${OPTION_CARD}`;

export function RadioOption({ name, value, checked, onSelect, children }: RadioOptionProps) {
  return (
    <label className={OPTION}>
      <input type="radio" name={name} value={value} checked={checked} onChange={onSelect} className="peer sr-only" />
      <span
        aria-hidden="true"
        className="size-4.5 flex-none rounded-full border-2 border-chevron bg-surface peer-checked:border-5 peer-checked:border-label"
      />
      {children}
    </label>
  );
}

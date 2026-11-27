"use client";

import { useId } from "react";
import { Chevron } from "./Chevron";
import { FIELD_CLASSES, FILTER_CLASSES } from "./fieldStyles";
import { SelectPanel } from "./select/SelectPanel";
import type { SelectOption } from "./select/selectModel";
import { useSelect } from "./select/useSelect";
import { ToneDot } from "./StatusDot";

export type { SelectOption };

export type SelectVariant = "field" | "filter" | "inline";

interface SelectProps<V extends string> {
  value: V;
  options: readonly SelectOption<V>[];
  onChange: (value: V) => void;
  label?: string;
  id?: string;
  name?: string;
  disabled?: boolean;
  variant?: SelectVariant;
  className?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
}

const VARIANTS: Record<SelectVariant, string> = {
  field: `${FIELD_CLASSES} h-9 w-full pr-3 pl-3 aria-expanded:shadow-field-focus`,
  filter: `${FILTER_CLASSES} max-w-full pr-2.5 pl-3`,
  inline: "h-7 rounded-nav bg-transparent px-2 text-callout text-label outline-none hover:bg-fill-plain-hover focus-visible:shadow-field-focus aria-expanded:bg-fill-plain-hover",
};

export function Select<V extends string>(props: SelectProps<V>) {
  const { value, options, onChange, label, id, name, disabled = false, variant = "field", className = "" } = props;
  const fallbackId = useId();
  const triggerId = id ?? fallbackId;
  const { triggerRef, panelRef, searchRef, view: state } = useSelect(options, value, onChange);
  const current = options.find((option) => option.value === value);
  const activeId = state.open && !state.searchable && state.active >= 0 ? state.optionId(state.active) : undefined;
  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        id={triggerId}
        role="combobox"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={state.open}
        aria-controls={state.open ? state.listId : undefined}
        aria-activedescendant={activeId}
        aria-describedby={props["aria-describedby"]}
        aria-invalid={props["aria-invalid"]}
        disabled={disabled}
        onClick={state.toggle}
        onKeyDown={state.onTriggerKey}
        className={`inline-flex min-w-0 cursor-pointer items-center gap-2 text-left disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      >
        {current?.tone ? <ToneDot tone={current.tone} /> : null}
        <span className="min-w-0 flex-1 truncate">{current?.label}</span>
        <Chevron direction="down" className="h-1.5 w-2.5 flex-none text-secondary" />
      </button>
      {name ? <input type="hidden" name={name} value={value} /> : null}
      {state.open ? (
        <SelectPanel
          state={state}
          options={options}
          value={value}
          naming={label ? { "aria-label": label } : { "aria-labelledby": triggerId }}
          panelRef={panelRef}
          searchRef={searchRef}
        />
      ) : null}
    </>
  );
}

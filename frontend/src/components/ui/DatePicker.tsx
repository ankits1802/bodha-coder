"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";
import { localIsoDate } from "@/lib/dates";
import { CalendarIcon } from "./date/CalendarIcon";
import { CalendarPopover } from "./date/CalendarPopover";
import { useDateText } from "./date/useDateText";
import { fieldLabelId } from "./Field";
import { FIELD_CLASSES, FILTER_CLASSES } from "./fieldStyles";
import { UI_TEXT } from "./strings";
import { useFloating } from "./useFloating";

export type DatePickerVariant = "field" | "filter";

export interface DatePickerProps {
  value: string | null;
  onChange: (value: string | null) => void;
  min?: string;
  max?: string;
  today?: string;
  label?: string;
  id?: string;
  name?: string;
  disabled?: boolean;
  variant?: DatePickerVariant;
  className?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
}

const CALENDAR_HEIGHT = 380;
const BOXES: Record<DatePickerVariant, string> = { field: "w-full", filter: "w-37" };
const INPUTS: Record<DatePickerVariant, string> = {
  field: `${FIELD_CLASSES} h-9 w-full pr-10 pl-3`,
  filter: `${FILTER_CLASSES} w-full pr-8 pl-3`,
};
const BUTTONS: Record<DatePickerVariant, string> = { field: "right-1 size-7", filter: "right-0.5 size-6.5" };

export function DatePicker(props: DatePickerProps) {
  const { value, onChange, min, max, label, id, name, disabled = false, variant = "field", className = "" } = props;
  const anchor = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const buttonId = useId();
  const [localToday] = useState(() => localIsoDate());
  const float = useFloating(anchor, panel);
  const text = useDateText(value, onChange, min, max);
  const words = UI_TEXT.date;
  const naming = label
    ? { "aria-label": words.chooseFor(label) }
    : { "aria-label": words.choose, "aria-labelledby": id ? `${buttonId} ${fieldLabelId(id)}` : undefined };

  function close(): void {
    float.hide();
    button.current?.focus();
  }

  function pick(day: string): void {
    text.revert();
    close();
    if (day !== value) onChange(day);
  }

  function onFieldKey(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.altKey && event.key === "ArrowDown") {
      event.preventDefault();
      float.show(CALENDAR_HEIGHT);
    } else if (event.key === "Escape" && text.editing) {
      event.preventDefault();
      event.stopPropagation();
      text.revert();
    }
  }

  return (
    <div ref={anchor} className={`relative ${BOXES[variant]} ${className}`}>
      <input
        id={id}
        type="text"
        autoComplete="off"
        aria-label={label}
        aria-describedby={props["aria-describedby"]}
        aria-invalid={props["aria-invalid"] || text.invalid || undefined}
        disabled={disabled}
        value={text.shown}
        onChange={(event) => text.type(event.target.value)}
        onBlur={text.settle}
        onKeyDown={onFieldKey}
        className={`${INPUTS[variant]} tabular-nums`}
      />
      <button
        ref={button}
        id={buttonId}
        type="button"
        {...naming}
        aria-haspopup="dialog"
        aria-expanded={float.style !== null}
        disabled={disabled}
        onClick={() => (float.style ? float.hide() : float.show(CALENDAR_HEIGHT))}
        className={`absolute inset-y-0 my-auto flex cursor-pointer items-center justify-center rounded-full text-secondary hover:bg-fill-plain-hover disabled:cursor-not-allowed disabled:text-quaternary ${BUTTONS[variant]}`}
      >
        <CalendarIcon />
      </button>
      {name ? <input type="hidden" name={name} value={value ?? ""} /> : null}
      {float.style ? (
        <CalendarPopover
          value={value}
          today={props.today ?? localToday}
          min={min}
          max={max}
          style={float.style}
          panelRef={panel}
          onPick={pick}
          onClose={close}
        />
      ) : null}
    </div>
  );
}

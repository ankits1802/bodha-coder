"use client";

import { useRef, type ClipboardEvent, type KeyboardEvent } from "react";

export const CODE_LENGTH = 6;

interface CodeInputProps {
  value: string;
  onChange: (value: string) => void;
  label: string;
  digitLabel: (position: number) => string;
  disabled?: boolean;
  autoFocus?: boolean;
}

function digitsOnly(text: string): string {
  return text.replace(/\D/g, "");
}

export function CodeInput({ value, onChange, label, digitLabel, disabled = false, autoFocus = false }: CodeInputProps) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length: CODE_LENGTH }, (_, index) => value.charAt(index));

  function focusAt(index: number): void {
    refs.current[Math.max(0, Math.min(CODE_LENGTH - 1, index))]?.focus();
  }

  function fill(start: number, typed: string): void {
    const clean = digitsOnly(typed);
    if (!clean) return;
    const next = (value.slice(0, start) + clean).slice(0, CODE_LENGTH);
    onChange(next);
    focusAt(next.length);
  }

  function onTyped(index: number, typed: string): void {
    const current = digits[index] ?? "";
    fill(index, typed.length > 1 && current ? typed.replace(current, "") : typed);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>, index: number): void {
    if (event.key === "ArrowLeft") focusAt(index - 1);
    if (event.key === "ArrowRight") focusAt(index + 1);
    if (event.key !== "Backspace") return;
    event.preventDefault();
    if (digits[index]) {
      onChange(value.slice(0, index));
      return;
    }
    onChange(value.slice(0, Math.max(0, index - 1)));
    focusAt(index - 1);
  }

  function onPaste(event: ClipboardEvent<HTMLInputElement>, index: number): void {
    event.preventDefault();
    fill(index, event.clipboardData.getData("text"));
  }

  return (
    <div role="group" aria-label={label} className="flex justify-between gap-2">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => {
            refs.current[index] = node;
          }}
          value={digit}
          aria-label={digitLabel(index + 1)}
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          autoFocus={autoFocus && index === 0}
          disabled={disabled}
          onChange={(event) => onTyped(index, event.target.value)}
          onKeyDown={(event) => onKeyDown(event, index)}
          onPaste={(event) => onPaste(event, index)}
          onFocus={(event) => event.target.select()}
          className="h-14 w-11.5 min-w-0 rounded-field bg-surface text-center text-title font-medium tabular-nums text-label shadow-field outline-none focus:shadow-option-on disabled:bg-muted-panel"
        />
      ))}
    </div>
  );
}

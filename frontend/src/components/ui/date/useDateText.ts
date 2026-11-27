"use client";

import { useState } from "react";
import { isWithin } from "@/lib/dates";
import { formatCalendarDay, parseCalendarDay } from "@/lib/format";

export interface DateText {
  shown: string;
  invalid: boolean;
  editing: boolean;
  type: (text: string) => void;
  settle: () => void;
  revert: () => void;
}

export function useDateText(value: string | null, onChange: (value: string | null) => void, min?: string, max?: string): DateText {
  const [draft, setDraft] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);
  const accepted = (text: string): string | null => {
    const day = parseCalendarDay(text);
    return day && isWithin(day, min, max) ? day : null;
  };

  function type(text: string): void {
    setDraft(text);
    setInvalid(false);
    const day = text.trim() ? accepted(text) : null;
    if (!text.trim() && value !== null) onChange(null);
    if (day && day !== value) onChange(day);
  }

  function settle(): void {
    if (draft === null) return;
    if (!draft.trim() || accepted(draft)) setDraft(null);
    else setInvalid(true);
  }

  function revert(): void {
    setDraft(null);
    setInvalid(false);
  }

  const shown = draft ?? (value ? formatCalendarDay(value, "year") : "");
  return { shown, invalid, editing: draft !== null, type, settle, revert };
}

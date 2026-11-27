"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent, type RefObject } from "react";
import { addMonths, clampIsoDate, dayInMonth, isIsoDate, isWithin } from "@/lib/dates";
import { WEEK_STARTS_ON } from "@/lib/format";
import { buttonClasses } from "../buttonStyles";
import type { FloatingStyle } from "../floating";
import { UI_TEXT } from "../strings";
import { CalendarGrid } from "./CalendarGrid";
import { CalendarHeader } from "./CalendarHeader";
import { dayForKey, wrapTab } from "./calendarKeys";
import { viewOf } from "./calendarModel";

interface CalendarPopoverProps {
  value: string | null;
  today: string;
  min?: string;
  max?: string;
  style: FloatingStyle;
  panelRef: RefObject<HTMLDivElement | null>;
  onPick: (day: string) => void;
  onClose: () => void;
}

const FOCUSED_DAY = "button[tabindex='0']";

export function CalendarPopover({ value, today, min, max, style, panelRef, onPick, onClose }: CalendarPopoverProps) {
  const headingId = useId();
  const grid = useRef<HTMLTableElement>(null);
  const focusGrid = useRef(true);
  const [focused, setFocused] = useState(() => clampIsoDate(value && isIsoDate(value) ? value : today, min, max));
  const view = viewOf(focused);

  useEffect(() => {
    if (!focusGrid.current) return;
    focusGrid.current = false;
    grid.current?.querySelector<HTMLButtonElement>(FOCUSED_DAY)?.focus();
  }, [focused]);

  function moveTo(day: string | null, toGrid: boolean): void {
    const next = day ? clampIsoDate(day, min, max) : focused;
    if (next === focused) return;
    focusGrid.current = toGrid;
    setFocused(next);
  }

  function onDayKey(event: KeyboardEvent<HTMLButtonElement>): void {
    const next = dayForKey(focused, event.key, event.shiftKey, WEEK_STARTS_ON);
    if (!next) return;
    event.preventDefault();
    moveTo(next, true);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      onClose();
      return;
    }
    if (panelRef.current) wrapTab(event, panelRef.current);
  }

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      onKeyDown={onKeyDown}
      style={style}
      className="fixed z-30 w-76 overflow-y-auto rounded-float bg-surface p-3 shadow-float"
    >
      <CalendarHeader
        year={view.year}
        month={view.month}
        today={today}
        min={min}
        max={max}
        headingId={headingId}
        onShift={(months) => moveTo(addMonths(focused, months), false)}
        onJump={(year, month) => moveTo(dayInMonth(year, month, view.day), false)}
      />
      <CalendarGrid
        year={view.year}
        month={view.month}
        focused={focused}
        selected={value}
        today={today}
        min={min}
        max={max}
        labelledBy={headingId}
        gridRef={grid}
        onKey={onDayKey}
        onPick={onPick}
      />
      <div className="mt-2 flex justify-end border-t border-hairline pt-2.5">
        <button type="button" disabled={!isWithin(today, min, max)} onClick={() => onPick(today)} className={buttonClasses("secondary", "sm")}>
          {UI_TEXT.date.today}
        </button>
      </div>
    </div>
  );
}

"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";

export interface Segment<V extends string> {
  value: V;
  label: ReactNode;
  count?: number;
  accessibleLabel?: string;
}

interface SegmentedControlProps<V extends string> {
  label: string;
  value: V | null;
  segments: Segment<V>[];
  onChange: (value: V) => void;
  size?: "sm" | "md";
  orientation?: "both" | "horizontal";
}

const SIDE_KEYS: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 };
const NEXT_KEYS: Record<string, number> = { ...SIDE_KEYS, ArrowDown: 1, ArrowUp: -1 };

export function SegmentedControl<V extends string>(props: SegmentedControlProps<V>) {
  const { label, value, segments, onChange, size = "md", orientation = "both" } = props;
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const focusable = segments.some((segment) => segment.value === value) ? value : segments[0]?.value;
  const keys = orientation === "horizontal" ? SIDE_KEYS : NEXT_KEYS;

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const step = keys[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = (index + step + segments.length) % segments.length;
    const target = segments[next];
    if (!target) return;
    onChange(target.value);
    refs.current[next]?.focus();
  }

  return (
    <div role="radiogroup" aria-label={label} aria-orientation={orientation === "horizontal" ? "horizontal" : undefined} className="inline-flex max-w-full flex-wrap rounded-segment bg-control p-0.5">
      {segments.map((segment, index) => {
        const on = segment.value === value;
        return (
          <button
            key={segment.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role="radio"
            aria-checked={on}
            aria-label={segment.accessibleLabel}
            tabIndex={segment.value === focusable ? 0 : -1}
            onClick={() => onChange(segment.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={`${size === "sm" ? "h-6.5 px-2.5" : "h-7 px-3"} cursor-pointer rounded-nav text-subhead font-medium tracking-snug whitespace-nowrap text-label ${on ? "bg-surface shadow-segment-on" : "bg-transparent"}`}
          >
            {segment.label}
            {segment.count !== undefined ? (
              <span className="ml-1 font-normal text-label-soft tabular-nums">{segment.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

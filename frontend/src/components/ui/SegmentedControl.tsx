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
  value: V;
  segments: Segment<V>[];
  onChange: (value: V) => void;
  size?: "sm" | "md";
}

const NEXT_KEYS: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

export function SegmentedControl<V extends string>({ label, value, segments, onChange, size = "md" }: SegmentedControlProps<V>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const step = NEXT_KEYS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = (index + step + segments.length) % segments.length;
    const target = segments[next];
    if (!target) return;
    onChange(target.value);
    refs.current[next]?.focus();
  }

  return (
    <div role="radiogroup" aria-label={label} className="inline-flex max-w-full flex-wrap rounded-segment bg-control p-0.5">
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
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(segment.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={`${size === "sm" ? "h-6.5 px-2.5" : "h-7 px-3"} cursor-pointer rounded-nav text-subhead font-medium tracking-snug whitespace-nowrap text-label ${on ? "bg-surface shadow-segment-on" : "bg-transparent"}`}
          >
            {segment.label}
            {segment.count !== undefined ? (
              <span className="ml-1 font-normal text-tertiary tabular-nums">{segment.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

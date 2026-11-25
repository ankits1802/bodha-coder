"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

export interface TabItem<V extends string> {
  value: V;
  label: string;
}

interface TabsProps<V extends string> {
  label: string;
  tabs: TabItem<V>[];
  value: V;
  onChange: (value: V) => void;
  headerClassName?: string;
  children: ReactNode;
}

const STEPS: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 };

export function Tabs<V extends string>({ label, tabs, value, onChange, headerClassName = "", children }: TabsProps<V>) {
  const prefix = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const step = STEPS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = (index + step + tabs.length) % tabs.length;
    const target = tabs[next];
    if (!target) return;
    onChange(target.value);
    refs.current[next]?.focus();
  }

  return (
    <>
      <div className={headerClassName}>
        <div role="tablist" aria-label={label} className="inline-flex max-w-full flex-wrap rounded-segment bg-control p-0.5">
        {tabs.map((tab, index) => {
          const on = tab.value === value;
          return (
            <button
              key={tab.value}
              ref={(node) => {
                refs.current[index] = node;
              }}
              id={`${prefix}-tab-${tab.value}`}
              type="button"
              role="tab"
              aria-selected={on}
              aria-controls={`${prefix}-panel`}
              tabIndex={on ? 0 : -1}
              onClick={() => onChange(tab.value)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={`h-7 cursor-pointer rounded-nav px-3 text-subhead font-medium tracking-snug whitespace-nowrap text-label ${on ? "bg-surface shadow-segment-on" : "bg-transparent"}`}
            >
              {tab.label}
            </button>
          );
        })}
        </div>
      </div>
      <div id={`${prefix}-panel`} role="tabpanel" aria-labelledby={`${prefix}-tab-${value}`} tabIndex={0} className="outline-none">
        {children}
      </div>
    </>
  );
}

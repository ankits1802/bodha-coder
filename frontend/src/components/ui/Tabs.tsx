"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

export interface TabItem<V extends string> {
  value: V;
  label: string;
}

export type TabActivation = "automatic" | "manual";

interface TabsProps<V extends string> {
  label: string;
  tabs: TabItem<V>[];
  value: V;
  onChange: (value: V) => void;
  activation?: TabActivation;
  headerClassName?: string;
  panelClassName?: string;
  children: ReactNode;
}

const STEPS: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 };

function targetIndex(key: string, index: number, count: number): number | null {
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  const step = STEPS[key];
  return step === undefined ? null : (index + step + count) % count;
}

export function Tabs<V extends string>(props: TabsProps<V>) {
  const { label, tabs, value, onChange, activation = "automatic", headerClassName = "", panelClassName = "", children } = props;
  const prefix = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const next = targetIndex(event.key, index, tabs.length);
    const target = next === null ? undefined : tabs[next];
    if (next === null || !target) return;
    event.preventDefault();
    if (activation === "automatic") onChange(target.value);
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
      <div id={`${prefix}-panel`} role="tabpanel" aria-labelledby={`${prefix}-tab-${value}`} tabIndex={0} className={panelClassName || undefined}>
        {children}
      </div>
    </>
  );
}

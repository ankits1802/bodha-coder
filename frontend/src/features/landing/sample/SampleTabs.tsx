"use client";

import { useId } from "react";
import { ToneDot } from "@/components/ui/StatusDot";
import { useRovingTabs } from "../tabs/useRovingTabs";
import styles from "./sample.module.css";
import { SamplePanel } from "./SamplePanel";
import type { SampleNote } from "./samples";

export function SampleTabs({ label, samples }: { label: string; samples: readonly SampleNote[] }) {
  const { selected, choose, onKeyDown, refAt } = useRovingTabs(samples.length);
  const base = useId();
  return (
    <div className="flex flex-col gap-8">
      <div role="tablist" aria-label={label} className={styles.tablist}>
        {samples.map((sample, index) => (
          <button
            key={sample.key}
            ref={refAt(index)}
            id={`${base}-tab-${sample.key}`}
            type="button"
            role="tab"
            aria-selected={index === selected}
            aria-controls={`${base}-panel-${sample.key}`}
            tabIndex={index === selected ? 0 : -1}
            onClick={() => choose(index)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={styles.tab}
          >
            <span className="flex items-center gap-2 font-semibold">
              <ToneDot tone={sample.verdict.tone} />
              {sample.tab}
            </span>
            <span className={`text-subhead text-secondary ${styles.visit}`}>{sample.visit}</span>
          </button>
        ))}
      </div>
      {samples.map((sample, index) => (
        <SamplePanel
          key={sample.key}
          sample={sample}
          id={`${base}-panel-${sample.key}`}
          labelledBy={`${base}-tab-${sample.key}`}
          hidden={index !== selected}
        />
      ))}
    </div>
  );
}

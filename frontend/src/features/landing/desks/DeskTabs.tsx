"use client";

import { useId, type ReactNode } from "react";
import { cssVars } from "../motion/cssVars";
import styles from "./desks.module.css";
import { useRovingTabs } from "./useRovingTabs";

export interface DeskTab {
  key: string;
  label: string;
  panel: ReactNode;
}

const PHONE_COLUMNS = 3;

export function DeskTabs({ label, tabs }: { label: string; tabs: readonly DeskTab[] }) {
  const { selected, choose, onKeyDown, refAt } = useRovingTabs(tabs.length);
  const base = useId();
  const place = cssVars({ "--sel": selected, "--col": selected % PHONE_COLUMNS, "--row": Math.floor(selected / PHONE_COLUMNS) });
  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label={label} className={styles.tablist} style={place}>
        {tabs.map((tab, index) => (
          <button
            key={tab.key}
            ref={refAt(index)}
            id={`${base}-tab-${tab.key}`}
            type="button"
            role="tab"
            aria-selected={index === selected}
            aria-controls={`${base}-panel-${tab.key}`}
            tabIndex={index === selected ? 0 : -1}
            onClick={() => choose(index)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={styles.tab}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, index) => (
        <div
          key={tab.key}
          id={`${base}-panel-${tab.key}`}
          role="tabpanel"
          aria-labelledby={`${base}-tab-${tab.key}`}
          tabIndex={0}
          hidden={index !== selected}
          className={styles.panelWrap}
        >
          {tab.panel}
        </div>
      ))}
    </div>
  );
}

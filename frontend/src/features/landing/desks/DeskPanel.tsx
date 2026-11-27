import type { ReactNode } from "react";
import { cssVars } from "../motion/cssVars";
import styles from "./desks.module.css";

interface DeskPanelProps {
  title: string;
  points: readonly string[];
  visual: ReactNode;
}

function Tick() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" className={styles.tick}>
      <path d="M3.5 8.5l3 3 6-7" />
    </svg>
  );
}

export function DeskPanel({ title, points, visual }: DeskPanelProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.copy}>
        <h3 className="m-0 font-display text-large-title font-bold tracking-title">{title}</h3>
        <ul className="mt-6 mb-0 flex list-none flex-col gap-3.5 p-0">
          {points.map((point, index) => (
            <li key={point} className={styles.point} style={cssVars({ "--i": index })}>
              <Tick />
              {point}
            </li>
          ))}
        </ul>
      </div>
      <div aria-hidden="true" className={styles.stage} data-live="">
        {visual}
      </div>
    </div>
  );
}

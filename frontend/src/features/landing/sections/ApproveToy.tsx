"use client";

import { useState } from "react";
import { haptic } from "@/lib/haptics";
import styles from "./sections.module.css";

export function ApproveToy({ approve, approved }: { approve: string; approved: string }) {
  const [done, setDone] = useState(false);

  function press(): void {
    haptic(done ? "select" : "success");
    setDone(!done);
  }

  return (
    <button type="button" aria-pressed={done} onClick={press} className={`${styles.toy} ${done ? styles.toyDone : ""}`}>
      <svg viewBox="0 0 16 16" aria-hidden="true" className={styles.toyCheck}>
        <path d="M3.5 8.5l3 3 6-7" pathLength={1} />
      </svg>
      <span>{done ? approved : approve}</span>
    </button>
  );
}

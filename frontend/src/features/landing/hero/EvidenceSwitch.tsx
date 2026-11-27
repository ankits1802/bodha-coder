"use client";

import { useRef, useState } from "react";
import { Toggle } from "@/components/ui/Toggle";
import { haptic } from "@/lib/haptics";

export function EvidenceSwitch({ label }: { label: string }) {
  const [on, setOn] = useState(true);
  const ref = useRef<HTMLSpanElement>(null);

  function change(next: boolean): void {
    setOn(next);
    haptic("select");
    const scope = ref.current?.closest<HTMLElement>("[data-evidence]");
    if (!scope) return;
    scope.dataset.evidence = next ? "on" : "off";
    scope.dataset.touched = "true";
  }

  return (
    <span ref={ref} className="flex items-center gap-2 text-caption font-semibold text-secondary">
      <span aria-hidden="true">{label}</span>
      <Toggle label={label} checked={on} onChange={change} />
    </span>
  );
}

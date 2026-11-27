"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { sha256Hex } from "./fingerprint";
import { VERIFY_TEXT } from "./strings";

type Comparison = "checking" | "matches" | "differs" | null;

export function DocumentCheck({ expected }: { expected: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [comparison, setComparison] = useState<Comparison>(null);

  async function choose(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setComparison("checking");
    setComparison((await sha256Hex(file)) === expected ? "matches" : "differs");
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button size="sm" pending={comparison === "checking"} onClick={() => input.current?.click()}>
        {VERIFY_TEXT.checkPdf}
      </Button>
      <input
        ref={input}
        type="file"
        accept="application/pdf"
        aria-label={VERIFY_TEXT.pdfLabel}
        tabIndex={-1}
        className="sr-only"
        onChange={(event) => void choose(event)}
      />
      <span aria-live="polite">
        {comparison === "matches" ? <StatusDot tone="ok">{VERIFY_TEXT.matches}</StatusDot> : null}
        {comparison === "differs" ? <StatusDot tone="bad">{VERIFY_TEXT.differs}</StatusDot> : null}
      </span>
    </div>
  );
}

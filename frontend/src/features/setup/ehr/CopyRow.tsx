"use client";

import { Button } from "@/components/ui/Button";
import { useCopy } from "@/hooks/useCopy";
import { EHR_TEXT } from "./strings";

const words = EHR_TEXT;

export function CopyRow({ label, value }: { label: string; value: string }) {
  const copier = useCopy();
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-subhead font-medium text-label">{label}</span>
      <div className="flex flex-wrap items-center gap-2">
        <output aria-label={label} className="min-w-0 rounded-field bg-muted-panel px-3 py-2 text-callout font-medium break-all select-all">
          {value}
        </output>
        <Button size="sm" aria-label={words.copyLabel(label)} onClick={() => void copier.copy(value)}>
          {words.copy}
        </Button>
        {copier.state !== "idle" ? (
          <span role="status" className="text-subhead text-secondary">
            {copier.state === "copied" ? words.copied : words.copyFailed}
          </span>
        ) : null}
      </div>
    </div>
  );
}

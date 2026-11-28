"use client";

import { Button } from "@/components/ui/Button";
import { useCopy } from "@/hooks/useCopy";
import { saveFile } from "@/lib/download";
import { SHARED_TEXT } from "./strings";

export function RecoveryCodeList({ codes }: { codes: readonly string[] }) {
  const copier = useCopy();
  const words = SHARED_TEXT.recoveryCodes;
  const text = `${codes.join("\n")}\n`;

  return (
    <div className="flex flex-col gap-3">
      <ol
        aria-label={words.listLabel}
        className="m-0 grid list-none grid-cols-2 gap-x-6 gap-y-1.5 rounded-field bg-muted-panel p-4 text-callout font-medium tracking-normal tabular-nums select-all"
      >
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ol>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => void copier.copy(text)}>
          {words.copy}
        </Button>
        <Button size="sm" onClick={() => saveFile(new Blob([text], { type: "text/plain" }), words.fileName)}>
          {words.download}
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

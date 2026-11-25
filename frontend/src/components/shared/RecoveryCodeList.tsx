"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { saveFile } from "@/lib/download";
import { SHARED_TEXT } from "./strings";

type CopyState = "idle" | "copied" | "failed";

export function RecoveryCodeList({ codes }: { codes: readonly string[] }) {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const words = SHARED_TEXT.recoveryCodes;
  const text = `${codes.join("\n")}\n`;

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

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
        <Button size="sm" onClick={() => void copy()}>
          {words.copy}
        </Button>
        <Button size="sm" onClick={() => saveFile(new Blob([text], { type: "text/plain" }), words.fileName)}>
          {words.download}
        </Button>
        {copyState !== "idle" ? (
          <span role="status" className="text-subhead text-secondary">
            {copyState === "copied" ? words.copied : words.copyFailed}
          </span>
        ) : null}
      </div>
    </div>
  );
}

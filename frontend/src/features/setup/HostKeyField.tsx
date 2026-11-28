"use client";

import { useId } from "react";
import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { readHostKey } from "@/lib/api/clearinghouse";
import { DEFAULT_PORT, type ConnectionDraft, type DraftChange } from "./connectionModel";
import { CLEARINGHOUSE_TEXT } from "./strings";

interface HostKeyFieldProps {
  draft: ConnectionDraft;
  error?: string;
  onChange: DraftChange;
}

export function HostKeyField({ draft, error, onChange }: HostKeyFieldProps) {
  const read = useAction(readHostKey);
  const labelId = useId();
  const words = CLEARINGHOUSE_TEXT;

  async function fetchKey(): Promise<void> {
    const outcome = await read.run(draft.host.trim(), Number(draft.port || DEFAULT_PORT));
    if (outcome.ok) onChange({ host_key_sha256: outcome.value.host_key_sha256 });
  }

  return (
    <div className="flex flex-col gap-1.5 sm:col-span-2">
      <span id={labelId} className="text-subhead font-medium text-label">
        {words.hostKey}
      </span>
      <div className="flex flex-wrap items-center gap-3">
        {draft.host_key_sha256 ? (
          <code aria-labelledby={labelId} className="rounded-nav bg-control px-2 py-1 font-mono text-footnote break-all text-label select-all">
            {draft.host_key_sha256}
          </code>
        ) : (
          <span aria-labelledby={labelId} className="text-subhead text-secondary">
            {words.noHostKey}
          </span>
        )}
        <Button size="sm" pending={read.pending} disabled={!draft.host.trim()} onClick={() => void fetchKey()}>
          {words.readHostKey}
        </Button>
      </div>
      {error ? <span className="text-footnote text-bad-text">{error}</span> : null}
      {read.error ? (
        <span role="alert" className="text-footnote text-bad-text">
          {read.error}
        </span>
      ) : null}
    </div>
  );
}

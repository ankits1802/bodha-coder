"use client";

import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { downloadClaimFile, sendClaims } from "@/lib/api/claims";
import type { BillingRow, ClearinghouseSummary } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { formatCount } from "@/lib/format";
import { sendableIds } from "../claimStatus";
import { CLAIM_TEXT } from "../strings";

interface SendClaimsProps {
  clearinghouse: ClearinghouseSummary;
  rows: BillingRow[];
  onDone: (notice: string) => void;
}

export function SendClaims({ clearinghouse, rows, onDone }: SendClaimsProps) {
  const send = useAction(sendClaims);
  const download = useAction(downloadClaimFile);
  const ids = sendableIds(rows);
  const bySftp = clearinghouse.transport === "sftp";
  if (ids.length === 0) return null;

  async function runSend(): Promise<void> {
    download.clearError();
    const outcome = await send.run(ids);
    if (outcome.ok) onDone(CLAIM_TEXT.sent(outcome.value.claims));
  }

  async function runDownload(): Promise<void> {
    send.clearError();
    const outcome = await download.run(ids);
    if (!outcome.ok) return;
    saveFile(outcome.value.blob, outcome.value.fileName ?? CLAIM_TEXT.fileName);
    onDone(CLAIM_TEXT.downloaded);
  }

  const error = send.error ?? download.error;
  return (
    <span className="flex flex-wrap items-center gap-2">
      <Button variant={bySftp ? "secondary" : "primary"} pending={download.pending} disabled={send.pending} onClick={() => void runDownload()}>
        {CLAIM_TEXT.download}
      </Button>
      {bySftp ? (
        <Button variant="primary" pending={send.pending} disabled={download.pending} onClick={() => void runSend()}>
          {CLAIM_TEXT.send(formatCount(ids.length))}
        </Button>
      ) : null}
      {error ? (
        <span role="alert" className="basis-full text-footnote text-bad-text">
          {error}
        </span>
      ) : null}
    </span>
  );
}

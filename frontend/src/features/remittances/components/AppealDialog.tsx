"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { TextArea } from "@/components/ui/Input";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { downloadDefensePacket, getAppealDraft } from "@/lib/api/remittances";
import type { AppealDraft, RemittanceLine } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { formatCalendarDay } from "@/lib/format";
import { REMITTANCE_TEXT } from "../strings";

interface AppealDialogProps {
  line: RemittanceLine | null;
  onClose: () => void;
}

const REMOTE_TEXT = { loading: REMITTANCE_TEXT.loadingAppeal, empty: REMITTANCE_TEXT.noLines, retry: REMITTANCE_TEXT.retry };

async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

async function savePacket(path: string): Promise<void> {
  const file = await downloadDefensePacket(path);
  saveFile(file.blob, file.fileName ?? REMITTANCE_TEXT.defaultPacketName);
}

function LetterActions({ draft }: { draft: AppealDraft }) {
  const copy = useAction(copyText);
  const packet = useAction(savePacket);
  const [copied, setCopied] = useState(false);
  const packetPath = draft.defense_packet;

  async function copyLetter(): Promise<void> {
    setCopied(false);
    const outcome = await copy.run(draft.text);
    setCopied(outcome.ok);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" pending={copy.pending} onClick={() => void copyLetter()}>
          {REMITTANCE_TEXT.copy}
        </Button>
        <Button size="sm" onClick={() => saveFile(new Blob([draft.text], { type: "text/plain;charset=utf-8" }), draft.file_name)}>
          {REMITTANCE_TEXT.download}
        </Button>
        {packetPath ? (
          <Button size="sm" pending={packet.pending} onClick={() => void packet.run(packetPath)}>
            {REMITTANCE_TEXT.defensePacket}
          </Button>
        ) : null}
        {copied ? (
          <span role="status" className="text-footnote text-secondary">
            {REMITTANCE_TEXT.copied}
          </span>
        ) : null}
      </div>
      {copy.error ? <InlineAlert tone="bad">{copy.error}</InlineAlert> : null}
      {packet.error ? <InlineAlert tone="bad">{packet.error}</InlineAlert> : null}
    </div>
  );
}

function AppealBody({ lineId }: { lineId: string }) {
  const draft = useRemote(`appeal:${lineId}`, () => getAppealDraft(lineId));
  return (
    <RemoteView state={draft.state} text={REMOTE_TEXT} onRetry={draft.reload}>
      {(data) => (
        <>
          <TextArea readOnly aria-label={REMITTANCE_TEXT.appealLabel} value={data.text} rows={18} className="font-sans tabular-nums" />
          <LetterActions draft={data} />
        </>
      )}
    </RemoteView>
  );
}

export function AppealDialog({ line, onClose }: AppealDialogProps) {
  const due = line?.appeal_by ? REMITTANCE_TEXT.appealBy(formatCalendarDay(line.appeal_by, "year")) : undefined;
  return (
    <Dialog
      open={line !== null}
      onClose={onClose}
      title={REMITTANCE_TEXT.appealTitle}
      description={due}
      size="lg"
      footer={
        <Button variant="plain" onClick={onClose}>
          {REMITTANCE_TEXT.close}
        </Button>
      }
    >
      {line ? <AppealBody lineId={line.id} /> : null}
    </Dialog>
  );
}

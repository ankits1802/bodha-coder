"use client";

import { Button } from "@/components/ui/Button";
import type { ButtonSize } from "@/components/ui/buttonStyles";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAction } from "@/hooks/useAction";
import { downloadDefensePacket } from "@/lib/api/defensibility";
import { saveFile } from "@/lib/download";
import { DEFENSE_TEXT } from "./strings";

interface DefensePacketButtonProps {
  noteId: string;
  size?: ButtonSize;
}

export function DefensePacketButton({ noteId, size = "md" }: DefensePacketButtonProps) {
  const download = useAction(downloadDefensePacket);

  async function save(): Promise<void> {
    const outcome = await download.run(noteId);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? DEFENSE_TEXT.fileName);
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Button size={size} onClick={() => void save()} pending={download.pending} aria-label={DEFENSE_TEXT.downloadLabel}>
        {DEFENSE_TEXT.download}
      </Button>
      {download.error ? (
        <span role="alert">
          <StatusDot tone="bad">{download.error}</StatusDot>
        </span>
      ) : null}
    </span>
  );
}

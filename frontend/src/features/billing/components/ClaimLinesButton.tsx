"use client";

import { Button } from "@/components/ui/Button";
import { useAction } from "@/hooks/useAction";
import { downloadClaimLines } from "@/lib/api/billing";
import { saveFile } from "@/lib/download";
import { BILLING_TEXT } from "../strings";

export function ClaimLinesButton({ onExported }: { onExported: () => void }) {
  const download = useAction(downloadClaimLines);

  async function run(): Promise<void> {
    const outcome = await download.run();
    if (!outcome.ok) return;
    saveFile(outcome.value.blob, outcome.value.fileName ?? BILLING_TEXT.claimLinesFile);
    onExported();
  }

  return (
    <Button pending={download.pending} onClick={() => void run()}>
      {BILLING_TEXT.claimLines}
    </Button>
  );
}

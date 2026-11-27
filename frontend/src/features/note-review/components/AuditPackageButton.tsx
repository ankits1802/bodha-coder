"use client";

import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAction } from "@/hooks/useAction";
import { downloadAuditPackage } from "@/lib/api/defensibility";
import { saveFile } from "@/lib/download";
import { REVIEW_TEXT } from "../strings";

const FILE_NAME = "bodha-audit-package.zip";

export function AuditPackageButton({ noteId }: { noteId: string }) {
  const download = useAction(downloadAuditPackage);

  async function save(): Promise<void> {
    const outcome = await download.run(noteId);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? FILE_NAME);
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Button size="sm" onClick={() => void save()} pending={download.pending}>
        {REVIEW_TEXT.tools.auditPackage}
      </Button>
      {download.error ? (
        <span role="alert">
          <StatusDot tone="bad">{download.error}</StatusDot>
        </span>
      ) : null}
    </span>
  );
}

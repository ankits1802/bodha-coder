"use client";

import { TextButton } from "@/components/ui/TextButton";
import { useAction } from "@/hooks/useAction";
import { downloadAddendum } from "@/lib/api/queryGovernance";
import { saveFile } from "@/lib/download";
import { QUERY_TEXT } from "./strings";

interface ExportAddendumLinkProps {
  noteId: string;
  requestId: string;
}

async function saveAddendum(noteId: string, requestId: string): Promise<void> {
  const file = await downloadAddendum(noteId, requestId);
  saveFile(file.blob, file.fileName ?? QUERY_TEXT.defaultAddendumName);
}

export function ExportAddendumLink({ noteId, requestId }: ExportAddendumLinkProps) {
  const exporter = useAction(saveAddendum);
  return (
    <span className="flex flex-wrap items-center gap-3">
      <TextButton disabled={exporter.pending} onClick={() => void exporter.run(noteId, requestId)}>
        {QUERY_TEXT.exportAddendum}
      </TextButton>
      {exporter.error ? (
        <span role="alert" className="text-footnote text-bad-text">
          {exporter.error}
        </span>
      ) : null}
    </span>
  );
}

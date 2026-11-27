"use client";

import { CodeList } from "@/components/shared/CodeList";
import { TextButton } from "@/components/ui/TextButton";
import { useAction } from "@/hooks/useAction";
import { downloadExport } from "@/lib/api/billing";
import type { AttestationRecord, NoteExportRecord, SnapshotRecord } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { REVIEW_TEXT } from "../strings";
import { HistoryEntry, HistoryList, joinMeta } from "./HistoryEntry";

const words = REVIEW_TEXT.history;

export function SnapshotHistory({ snapshots }: { snapshots: SnapshotRecord[] }) {
  return (
    <HistoryList>
      {snapshots.map((snapshot) => (
        <HistoryEntry
          key={snapshot.id}
          at={snapshot.approved_at}
          title={<span className="font-medium">{words.revision(snapshot.revision)}</span>}
          meta={joinMeta([
            words.approvedBy(snapshot.approver_name, snapshot.approver_role),
            words.billedWas(snapshot.billed.join(", ")),
            words.provenance(snapshot.model ?? "—", snapshot.prompt_version ?? "—"),
            words.sha(snapshot.document_sha256),
          ])}
        >
          <CodeList codes={snapshot.codes} />
        </HistoryEntry>
      ))}
    </HistoryList>
  );
}

export function ExportHistory({ exports, canDownload }: { exports: NoteExportRecord[]; canDownload: boolean }) {
  const download = useAction(downloadExport);

  async function save(record: NoteExportRecord): Promise<void> {
    const outcome = await download.run(record.id);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? record.file_name);
  }

  return (
    <HistoryList>
      {exports.map((record) => (
        <HistoryEntry
          key={record.id}
          at={record.at}
          title={
            <>
              <span className="font-medium">{words.exportFormat[record.format]}</span>
              <span className="text-footnote text-secondary">{words.revision(record.snapshot_revision)}</span>
              {canDownload ? <TextButton onClick={() => void save(record)}>{words.download}</TextButton> : null}
            </>
          }
          meta={joinMeta([words.exportedBy(record.by, record.role, record.notes), record.again ? words.again : null, words.sha(record.sha256)])}
        />
      ))}
      {download.error ? (
        <li role="alert" className="text-footnote text-bad-text">
          {download.error}
        </li>
      ) : null}
    </HistoryList>
  );
}

export function AttestationHistory({ attestations }: { attestations: AttestationRecord[] }) {
  return (
    <HistoryList>
      {attestations.map((record) => (
        <HistoryEntry
          key={record.id}
          at={record.at}
          title={
            <>
              <span className="font-medium">{words.purpose[record.purpose]}</span>
              <span className="text-footnote text-secondary">{words.answer[record.answer]}</span>
            </>
          }
          meta={joinMeta([record.provider, words.confirmed(record.wording), record.ip ? words.from(record.ip) : null])}
        >
          <p className="m-0 text-callout whitespace-pre-wrap">{record.shown}</p>
          {record.comment ? <p className="m-0 text-callout">{record.comment}</p> : null}
        </HistoryEntry>
      ))}
    </HistoryList>
  );
}

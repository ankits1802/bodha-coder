import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Th } from "@/components/ui/Table";
import { UPLOAD_TEXT } from "../strings";
import { countByStatus, type References, type UploadEntry } from "../uploadEntries";
import { FilePicker } from "./FilePicker";
import { FileRow, type FileRowActions } from "./FileRow";

interface FileTableProps extends FileRowActions {
  entries: UploadEntry[];
  references: References;
  previewing: boolean;
  onFiles: (files: File[]) => void;
}

function Summary({ entries, previewing }: { entries: UploadEntry[]; previewing: boolean }) {
  const words = UPLOAD_TEXT.files;
  const counts = countByStatus(entries);
  return (
    <div className="flex flex-wrap items-center gap-4.5" aria-live="polite">
      <span className="text-body-lg font-semibold">{words.count(entries.length)}</span>
      {previewing ? <StatusDot tone="neutral">{words.reading}</StatusDot> : <StatusDot tone="ok">{words.ready(counts.ready)}</StatusDot>}
      {counts.check > 0 ? <StatusDot tone="warn">{words.check(counts.check)}</StatusDot> : null}
      {counts.fix > 0 ? <StatusDot tone="bad">{words.fix(counts.fix)}</StatusDot> : null}
      {counts.duplicate > 0 ? <StatusDot tone="warn">{words.duplicate(counts.duplicate)}</StatusDot> : null}
      {counts.uploaded > 0 ? <StatusDot tone="warn">{words.uploaded(counts.uploaded)}</StatusDot> : null}
      {counts.noCodes > 0 ? <StatusDot tone="neutral">{words.noCodes(counts.noCodes)}</StatusDot> : null}
    </div>
  );
}

export function FileTable({ entries, references, previewing, onFiles, ...actions }: FileTableProps) {
  const words = UPLOAD_TEXT.table;
  return (
    <section aria-label={UPLOAD_TEXT.files.label} className="overflow-hidden rounded-panel bg-surface shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-separator px-4 py-3.5">
        <Summary entries={entries} previewing={previewing} />
        <FilePicker onFiles={onFiles} label={UPLOAD_TEXT.files.add} />
      </div>
      <Table label={UPLOAD_TEXT.files.label} minWidth="xl">
        <thead>
          <tr>
            <Th>{words.patient}</Th>
            <Th>{words.provider}</Th>
            <Th>{words.date}</Th>
            <Th>{words.place}</Th>
            <Th>{words.billed}</Th>
            <Th>{words.visitType}</Th>
            <Th>{words.status}</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <FileRow key={entry.id} entry={entry} references={references} {...actions} />
          ))}
        </tbody>
      </Table>
    </section>
  );
}

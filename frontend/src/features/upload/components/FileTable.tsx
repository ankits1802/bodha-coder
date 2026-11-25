import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Th } from "@/components/ui/Table";
import { UPLOAD_TEXT } from "../strings";
import { countByStatus, type UploadEntry } from "../uploadEntries";
import { DropArea, FilePicker } from "./FilePicker";
import { FileRow } from "./FileRow";

interface FileTableProps {
  entries: UploadEntry[];
  onFiles: (files: File[]) => void;
  onUpdate: (id: string, change: Partial<Pick<UploadEntry, "billed" | "visitType" | "keep">>) => void;
  onRemove: (id: string) => void;
}

function Summary({ entries }: { entries: UploadEntry[] }) {
  const words = UPLOAD_TEXT.files;
  const counts = countByStatus(entries);
  return (
    <div className="flex flex-wrap items-center gap-4.5">
      <span className="text-body-lg font-semibold">{words.count(entries.length)}</span>
      <StatusDot tone="ok">{words.ready(counts.ready)}</StatusDot>
      {counts.fix > 0 ? <StatusDot tone="bad">{words.fix(counts.fix)}</StatusDot> : null}
      {counts.duplicate > 0 ? <StatusDot tone="warn">{words.duplicate(counts.duplicate)}</StatusDot> : null}
      {counts.noCodes > 0 ? <StatusDot tone="neutral">{words.noCodes(counts.noCodes)}</StatusDot> : null}
    </div>
  );
}

export function FileTable({ entries, onFiles, onUpdate, onRemove }: FileTableProps) {
  const words = UPLOAD_TEXT.table;
  return (
    <DropArea onFiles={onFiles} label={UPLOAD_TEXT.files.label} className="overflow-hidden rounded-panel bg-surface shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-separator px-4 py-3.5">
        <Summary entries={entries} />
        <FilePicker onFiles={onFiles} label={UPLOAD_TEXT.files.add} />
      </div>
      <Table label={UPLOAD_TEXT.files.label} minWidth="lg">
        <thead>
          <tr>
            <Th>{words.patient}</Th>
            <Th>{words.billed}</Th>
            <Th>{words.visitType}</Th>
            <Th>{words.check}</Th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <FileRow key={entry.id} entry={entry} onUpdate={onUpdate} onRemove={onRemove} />
          ))}
        </tbody>
      </Table>
    </DropArea>
  );
}

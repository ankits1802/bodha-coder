import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { Td, Tr } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import { UPLOAD_TEXT } from "../strings";
import { entryStatus, type EntryStatus, type UploadEntry } from "../uploadEntries";
import { FileRowInputs } from "./FileRowInputs";

const TONES: Record<EntryStatus, StatusTone> = { ready: "ok", fix: "bad", duplicate: "warn", noCodes: "neutral" };

interface FileRowProps {
  entry: UploadEntry;
  onUpdate: (id: string, change: Partial<Pick<UploadEntry, "billed" | "visitType" | "keep">>) => void;
  onRemove: (id: string) => void;
}

export function FileRow({ entry, onUpdate, onRemove }: FileRowProps) {
  const words = UPLOAD_TEXT.row;
  const status = entryStatus(entry);
  return (
    <Tr>
      <Td className="align-top">
        <span className={`font-medium ${entry.patientName ? "" : "text-secondary"}`}>{entry.patientName ?? words.readFromNote}</span>
        <span className="mt-0.5 block text-caption break-all text-tertiary">{entry.file.name}</span>
      </Td>
      {status === "duplicate" ? (
        <Td colSpan={2} className="align-top text-secondary">
          {words.sameAsAbove}
        </Td>
      ) : (
        <FileRowInputs entry={entry} name={entry.patientName ?? entry.file.name} onUpdate={onUpdate} />
      )}
      <Td className="align-top">
        <span className="flex flex-wrap items-center gap-3">
          <StatusDot tone={TONES[status]}>{UPLOAD_TEXT.status[status]}</StatusDot>
          {status === "duplicate" ? (
            <TextButton className="text-subhead" aria-label={words.keepLabel(entry.file.name)} onClick={() => onUpdate(entry.id, { keep: true })}>
              {words.keep}
            </TextButton>
          ) : null}
          <TextButton className="text-subhead" aria-label={words.removeLabel(entry.file.name)} onClick={() => onRemove(entry.id)}>
            {UPLOAD_TEXT.table.remove}
          </TextButton>
        </span>
      </Td>
    </Tr>
  );
}

import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { Td } from "@/components/ui/Table";
import { TextButton } from "@/components/ui/TextButton";
import { UPLOAD_TEXT } from "../strings";
import { entryStatus, hasPlacement, type EntryStatus, type UploadEntry } from "../uploadEntries";

const TONES: Record<EntryStatus, StatusTone> = { ready: "ok", check: "warn", fix: "bad", duplicate: "warn", uploaded: "warn", noCodes: "neutral" };

interface FileStatusCellProps {
  entry: UploadEntry;
  onKeep: (id: string) => void;
  onConfirm: (id: string) => void;
  onRemove: (id: string) => void;
}

export function FileStatusCell({ entry, onKeep, onConfirm, onRemove }: FileStatusCellProps) {
  const words = UPLOAD_TEXT.row;
  const status = entryStatus(entry);
  const confirmable = status === "check" && entry.check && hasPlacement(entry);
  return (
    <Td className="align-top">
      <span className="flex flex-wrap items-center gap-3">
        <StatusDot tone={TONES[status]}>{UPLOAD_TEXT.status[status]}</StatusDot>
        {status === "duplicate" ? (
          <TextButton className="text-subhead" aria-label={words.keepLabel(entry.file.name)} onClick={() => onKeep(entry.id)}>
            {words.keep}
          </TextButton>
        ) : null}
        {confirmable ? (
          <TextButton className="text-subhead" aria-label={words.confirmLabel(entry.file.name)} onClick={() => onConfirm(entry.id)}>
            {words.confirm}
          </TextButton>
        ) : null}
        <TextButton className="text-subhead" aria-label={words.removeLabel(entry.file.name)} onClick={() => onRemove(entry.id)}>
          {UPLOAD_TEXT.table.remove}
        </TextButton>
      </span>
    </Td>
  );
}

import { Td, Tr } from "@/components/ui/Table";
import { UPLOAD_TEXT } from "../strings";
import { entryStatus, type EntryEdit, type Placement, type References, type UploadEntry } from "../uploadEntries";
import { FilePlacementCells } from "./FilePlacementCells";
import { FileRowInputs } from "./FileRowInputs";
import { FileStatusCell } from "./FileStatusCell";

export interface FileRowActions {
  onUpdate: (id: string, change: EntryEdit) => void;
  onPlace: (id: string, change: Partial<Placement>) => void;
  onConfirm: (id: string) => void;
  onRemove: (id: string) => void;
}

interface FileRowProps extends FileRowActions {
  entry: UploadEntry;
  references: References;
}

export function FileRow({ entry, references, onUpdate, onPlace, onConfirm, onRemove }: FileRowProps) {
  const words = UPLOAD_TEXT.row;
  const status = entryStatus(entry);
  const name = entry.patientName ?? entry.file.name;
  const leftOut = status === "duplicate" || status === "uploaded";
  return (
    <Tr>
      <Td className="align-top">
        <span className={`font-medium ${entry.patientName ? "" : "text-secondary"}`}>{entry.patientName ?? words.readFromNote}</span>
        <span className="mt-0.5 block text-caption break-all text-tertiary">{entry.file.name}</span>
      </Td>
      {leftOut ? (
        <Td colSpan={5} className="align-top text-secondary">
          {status === "duplicate" ? words.sameAsAbove : null}
        </Td>
      ) : (
        <>
          <FilePlacementCells entry={entry} name={name} references={references} onPlace={onPlace} />
          <FileRowInputs entry={entry} name={name} onUpdate={onUpdate} />
        </>
      )}
      <FileStatusCell entry={entry} onKeep={(id) => onUpdate(id, { keep: true })} onConfirm={onConfirm} onRemove={onRemove} />
    </Tr>
  );
}

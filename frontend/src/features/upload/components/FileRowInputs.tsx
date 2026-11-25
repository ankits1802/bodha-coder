import { Input, Select } from "@/components/ui/Input";
import { Td } from "@/components/ui/Table";
import { VISIT_TYPES } from "@/lib/labels";
import { UPLOAD_TEXT } from "../strings";
import { invalidCodes, type UploadEntry } from "../uploadEntries";

interface FileRowInputsProps {
  entry: UploadEntry;
  name: string;
  onUpdate: (id: string, change: Partial<Pick<UploadEntry, "billed" | "visitType">>) => void;
}

export function FileRowInputs({ entry, name, onUpdate }: FileRowInputsProps) {
  const words = UPLOAD_TEXT.row;
  const invalid = invalidCodes(entry);
  const errorId = `${entry.id}-error`;
  return (
    <>
      <Td className="w-1/3 align-top">
        <Input
          aria-label={words.billedLabel(name)}
          aria-invalid={invalid.length > 0 ? true : undefined}
          aria-describedby={invalid.length > 0 ? errorId : undefined}
          value={entry.billed ?? ""}
          placeholder={words.optional}
          onChange={(event) => onUpdate(entry.id, { billed: event.target.value })}
          className="font-medium tabular-nums"
        />
        {invalid.length > 0 ? (
          <span id={errorId} className="mt-1.5 block text-footnote text-bad-text">
            {words.invalid(invalid.join(", "))}
          </span>
        ) : null}
      </Td>
      <Td className="align-top">
        <Select
          aria-label={words.visitLabel(name)}
          value={entry.visitType ?? ""}
          onChange={(event) => onUpdate(entry.id, { visitType: event.target.value || null })}
        >
          <option value="">{words.sameAsBatch}</option>
          {VISIT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </Select>
      </Td>
    </>
  );
}

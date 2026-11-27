import { DatePicker } from "@/components/ui/DatePicker";
import { Select } from "@/components/ui/Select";
import { Td } from "@/components/ui/Table";
import { UPLOAD_TEXT } from "../strings";
import type { Placement, References, UploadEntry } from "../uploadEntries";
import { placeOptions, providerOptions } from "./placementOptions";

interface FilePlacementCellsProps {
  entry: UploadEntry;
  name: string;
  references: References;
  onPlace: (id: string, change: Partial<Placement>) => void;
}

export function FilePlacementCells({ entry, name, references, onPlace }: FilePlacementCellsProps) {
  const words = UPLOAD_TEXT.row;
  return (
    <>
      <Td className="min-w-44 align-top">
        <Select
          label={words.providerLabel(name)}
          value={entry.providerId}
          options={providerOptions(references.providers, words.chooseProvider)}
          onChange={(providerId) => onPlace(entry.id, { providerId })}
        />
      </Td>
      <Td className="min-w-36 align-top">
        <DatePicker
          label={words.dateLabel(name)}
          value={entry.serviceDate || null}
          onChange={(day) => onPlace(entry.id, { serviceDate: day ?? "" })}
        />
      </Td>
      <Td className="min-w-40 align-top">
        <Select
          label={words.placeLabel(name)}
          value={entry.placeCode}
          options={placeOptions(references.places, words.choosePlace)}
          onChange={(placeCode) => onPlace(entry.id, { placeCode })}
        />
      </Td>
    </>
  );
}

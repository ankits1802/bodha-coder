import { Select } from "@/components/ui/Select";
import { Td } from "@/components/ui/Table";
import type { PayerOption } from "@/lib/api/types";
import { UPLOAD_TEXT } from "../strings";
import type { UploadEntry } from "../uploadEntries";
import { payerOptions } from "../uploadPayers";

interface FilePayerCellProps {
  entry: UploadEntry;
  name: string;
  payers: PayerOption[];
  onPayer: (id: string, payerId: string) => void;
}

export function FilePayerCell({ entry, name, payers, onPayer }: FilePayerCellProps) {
  return (
    <Td className="min-w-40 align-top">
      <Select
        label={UPLOAD_TEXT.row.payerLabel(name)}
        value={entry.payerId}
        options={payerOptions(payers, entry.suggestedPayer)}
        onChange={(payerId) => onPayer(entry.id, payerId)}
      />
    </Td>
  );
}

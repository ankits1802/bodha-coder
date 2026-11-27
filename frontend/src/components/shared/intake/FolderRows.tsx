import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Provider } from "@/lib/api/types";
import type { FolderRow } from "./intakeForm";
import { INTAKE_TEXT } from "./strings";

interface FolderRowsProps {
  rows: FolderRow[];
  providers: Provider[];
  problems: Record<number, string>;
  onChange: (row: FolderRow) => void;
  onRemove: (rowId: number) => void;
}

export function FolderRows({ rows, providers, problems, onChange, onRemove }: FolderRowsProps) {
  const active = providers.filter((provider) => provider.active);
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {rows.map((row, index) => {
        const number = index + 1;
        const problem = problems[row.id];
        const errorId = `intake-folder-${row.id}-error`;
        return (
          <li key={row.id} className="flex flex-col gap-1">
            <span className="flex flex-wrap items-center gap-2">
              <Input
                aria-label={INTAKE_TEXT.folderLabel(number)}
                aria-invalid={problem ? true : undefined}
                aria-describedby={problem ? errorId : undefined}
                value={row.folder}
                onChange={(event) => onChange({ ...row, folder: event.target.value })}
                className="max-w-56"
              />
              <Select
                label={INTAKE_TEXT.providerLabel(number)}
                value={row.providerId}
                options={[{ value: "", label: INTAKE_TEXT.chooseProvider }, ...active.map((provider) => ({ value: provider.id, label: provider.name }))]}
                onChange={(providerId) => onChange({ ...row, providerId })}
                className="max-w-64"
              />
              <Button size="sm" variant="plain" aria-label={INTAKE_TEXT.removeLabel(number)} onClick={() => onRemove(row.id)}>
                {INTAKE_TEXT.remove}
              </Button>
            </span>
            {problem ? (
              <span id={errorId} className="text-footnote text-bad-text">
                {problem}
              </span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

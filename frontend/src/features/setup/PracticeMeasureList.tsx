import { Button } from "@/components/ui/Button";
import { TextButton } from "@/components/ui/TextButton";
import type { PracticeMeasure } from "@/lib/api/types";
import { PRACTICE_MEASURE_TEXT } from "./strings";

interface PracticeMeasureListProps {
  measures: PracticeMeasure[];
  chosen: Set<string>;
  onToggle: (key: string, on: boolean) => void;
  onAdd: () => void;
  onEdit: (measure: PracticeMeasure) => void;
  onRetire: (measure: PracticeMeasure) => void;
}

const words = PRACTICE_MEASURE_TEXT;

export function PracticeMeasureList({ measures, chosen, onToggle, onAdd, onEdit, onRetire }: PracticeMeasureListProps) {
  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-1 px-4 text-caption font-semibold text-tertiary">{words.group}</legend>
      <ul className="m-0 list-none p-0">
        {measures.map((measure) => (
          <li key={measure.key} className="flex min-h-11 flex-wrap items-center gap-x-4 gap-y-1 border-t border-hairline px-4 py-2">
            <label className="flex min-w-0 flex-[1_1_16rem] cursor-pointer items-center gap-3 text-body">
              <input
                type="checkbox"
                checked={chosen.has(measure.key)}
                onChange={(event) => onToggle(measure.key, event.target.checked)}
                className="size-4 flex-none accent-label"
              />
              <span className="min-w-0">
                {measure.name}
                {measure.identifier ? <span className="ml-2 text-secondary">{measure.identifier}</span> : null}
              </span>
            </label>
            <span className="flex gap-4 text-subhead">
              <TextButton aria-label={words.editFor(measure.name)} onClick={() => onEdit(measure)}>
                {words.edit}
              </TextButton>
              <TextButton tone="warn" aria-label={words.retireFor(measure.name)} onClick={() => onRetire(measure)}>
                {words.retire}
              </TextButton>
            </span>
          </li>
        ))}
      </ul>
      <div className="border-t border-hairline px-4 pt-3">
        <Button size="sm" onClick={onAdd}>
          {words.add}
        </Button>
      </div>
    </fieldset>
  );
}

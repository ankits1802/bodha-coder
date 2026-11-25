import type { MipsMeasure } from "@/lib/api/types";

interface MeasureListProps {
  legend: string;
  measures: MipsMeasure[];
  chosen: Set<string> | null;
  onToggle: (id: string, on: boolean) => void;
}

export function MeasureList({ legend, measures, chosen, onToggle }: MeasureListProps) {
  if (measures.length === 0) return null;
  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-1 px-4 text-caption font-semibold text-tertiary">{legend}</legend>
      <ul className="m-0 list-none p-0">
        {measures.map((measure) => (
          <li key={measure.id} className="border-t border-hairline">
            {chosen ? (
              <label className="flex min-h-11 cursor-pointer items-center gap-3 px-4 py-2 text-body">
                <input
                  type="checkbox"
                  checked={chosen.has(measure.id)}
                  onChange={(event) => onToggle(measure.id, event.target.checked)}
                  className="size-4 flex-none accent-label"
                />
                <span className="w-12 flex-none font-semibold tabular-nums">{measure.id}</span>
                <span className="min-w-0">{measure.title}</span>
              </label>
            ) : (
              <span className="flex min-h-11 items-center gap-3 px-4 py-2 text-body">
                <span className="w-12 flex-none font-semibold tabular-nums">{measure.id}</span>
                <span className="min-w-0">{measure.title}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </fieldset>
  );
}

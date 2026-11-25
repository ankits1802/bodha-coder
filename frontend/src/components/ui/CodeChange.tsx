import { CodeChip } from "./CodeChip";

interface CodeChangeProps {
  before: string | null;
  after: string | null;
  addedLabel: string;
  changedLabel: string;
}

export function CodeChange({ before, after, addedLabel, changedLabel }: CodeChangeProps) {
  if (before && after && before !== after) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CodeChip code={before} variant="old" />
        <span aria-hidden="true" className="text-quaternary">
          →
        </span>
        <span className="sr-only">{changedLabel}</span>
        <CodeChip code={after} variant="new" />
      </span>
    );
  }
  if (!before && after) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="text-footnote text-secondary">{addedLabel}</span>
        <CodeChip code={after} variant="new" />
      </span>
    );
  }
  return before ? <CodeChip code={before} /> : null;
}

import { CodeChip } from "@/components/ui/CodeChip";
import { FORMAT_WORDS } from "@/lib/format";

interface CodeListProps {
  codes: string[];
  max?: number;
}

export function CodeList({ codes, max }: CodeListProps) {
  if (codes.length === 0) return <span className="text-quaternary">{FORMAT_WORDS.empty}</span>;
  const shown = max === undefined ? codes : codes.slice(0, max);
  const hidden = codes.length - shown.length;
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {shown.map((code) => (
        <CodeChip key={code} code={code} />
      ))}
      {hidden > 0 ? <span className="text-footnote text-tertiary">+{hidden}</span> : null}
    </span>
  );
}

import { formatCount } from "@/lib/format";
import { Button } from "./Button";

export interface PagerText {
  label: string;
  previous: string;
  next: string;
  range: (first: string, last: string, total: string) => string;
}

interface PagerProps {
  offset: number;
  pageSize: number;
  shown: number;
  total: number;
  text: PagerText;
  onOffset: (offset: number) => void;
}

export function Pager({ offset, pageSize, shown, total, text, onOffset }: PagerProps) {
  const hasPrevious = offset > 0;
  const hasNext = offset + shown < total;
  if (!hasPrevious && !hasNext) return null;
  return (
    <nav aria-label={text.label} className="flex flex-wrap items-center justify-end gap-3">
      {shown > 0 ? (
        <span className="text-subhead text-secondary tabular-nums">
          {text.range(formatCount(offset + 1), formatCount(offset + shown), formatCount(total))}
        </span>
      ) : null}
      <span className="flex gap-2">
        <Button size="sm" disabled={!hasPrevious} onClick={() => onOffset(Math.max(0, offset - pageSize))}>
          {text.previous}
        </Button>
        <Button size="sm" disabled={!hasNext} onClick={() => onOffset(offset + pageSize)}>
          {text.next}
        </Button>
      </span>
    </nav>
  );
}

export function offsetFrom(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 0;
}

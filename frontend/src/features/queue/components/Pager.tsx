import { Button } from "@/components/ui/Button";
import { QUEUE_TEXT } from "../strings";

interface PagerProps {
  offset: number;
  pageSize: number;
  shown: number;
  onOffset: (offset: number) => void;
}

export function Pager({ offset, pageSize, shown, onOffset }: PagerProps) {
  const hasPrevious = offset > 0;
  const hasNext = shown >= pageSize;
  if (!hasPrevious && !hasNext) return null;
  return (
    <nav aria-label={QUEUE_TEXT.pager} className="flex justify-end gap-2">
      <Button size="sm" disabled={!hasPrevious} onClick={() => onOffset(Math.max(0, offset - pageSize))}>
        {QUEUE_TEXT.previous}
      </Button>
      <Button size="sm" disabled={!hasNext} onClick={() => onOffset(offset + pageSize)}>
        {QUEUE_TEXT.next}
      </Button>
    </nav>
  );
}

import { Button } from "@/components/ui/Button";
import { formatCount } from "@/lib/format";
import { QUEUE_TEXT } from "../strings";

interface BulkBarProps {
  count: number;
  pending: boolean;
  onClear: () => void;
  onApprove: () => void;
}

export function BulkBar({ count, pending, onClear, onApprove }: BulkBarProps) {
  if (count === 0) return null;
  const amount = formatCount(count);
  return (
    <div
      role="region"
      aria-label={QUEUE_TEXT.selectionBar}
      className="sticky bottom-5 flex flex-wrap items-center gap-4 self-center rounded-full bg-surface py-2 pr-2 pl-5 shadow-float"
    >
      <span className="text-body">
        <span className="font-semibold">{QUEUE_TEXT.selected(amount)}</span>
        <span className="text-secondary"> · {QUEUE_TEXT.allMatch}</span>
      </span>
      <Button variant="plain" size="sm" onClick={onClear} disabled={pending}>
        {QUEUE_TEXT.clear}
      </Button>
      <Button variant="primary" size="sm" pending={pending} onClick={onApprove}>
        {QUEUE_TEXT.approve(amount)}
      </Button>
    </div>
  );
}

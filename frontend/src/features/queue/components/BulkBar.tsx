import { Button } from "@/components/ui/Button";
import { formatCount } from "@/lib/format";
import type { BulkAbilities } from "../queueRules";
import { QUEUE_TEXT } from "../strings";

interface BulkBarProps {
  count: number;
  abilities: BulkAbilities;
  pending: boolean;
  onClear: () => void;
  onApprove: () => void;
  onAssign: () => void;
  onDelete: () => void;
}

export function BulkBar({ count, abilities, pending, onClear, onApprove, onAssign, onDelete }: BulkBarProps) {
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
        {abilities.approve ? <span className="text-secondary"> · {QUEUE_TEXT.allMatch}</span> : null}
      </span>
      <Button variant="plain" size="sm" onClick={onClear} disabled={pending}>
        {QUEUE_TEXT.clear}
      </Button>
      {abilities.remove ? (
        <Button variant="danger" size="sm" onClick={onDelete} disabled={pending}>
          {QUEUE_TEXT.delete(amount)}
        </Button>
      ) : null}
      {abilities.assign ? (
        <Button size="sm" onClick={onAssign} disabled={pending}>
          {QUEUE_TEXT.assign}
        </Button>
      ) : null}
      {abilities.approve ? (
        <Button variant="primary" size="sm" pending={pending} onClick={onApprove}>
          {QUEUE_TEXT.approve(amount)}
        </Button>
      ) : null}
    </div>
  );
}

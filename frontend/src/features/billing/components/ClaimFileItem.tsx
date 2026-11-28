import { Button } from "@/components/ui/Button";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { sentence } from "@/lib/api/errors";
import type { ClaimFileOutcome, ClaimFileRecord } from "@/lib/api/types";
import { formatCount, formatDateTime, formatMoney } from "@/lib/format";
import { CLAIM_FILE_TEXT } from "../strings";

const OUTCOME_TONES: Record<ClaimFileOutcome, StatusTone> = {
  sending: "low",
  delivered: "ok",
  downloaded: "ok",
  failed: "bad",
};

interface ClaimFileItemProps {
  record: ClaimFileRecord;
  onDownload: (record: ClaimFileRecord) => void;
}

function acknowledgment(record: ClaimFileRecord): string | null {
  const parts: string[] = [];
  if (record.file_ack) parts.push(CLAIM_FILE_TEXT.fileAck[record.file_ack]);
  if (record.accepted + record.rejected > 0) parts.push(CLAIM_FILE_TEXT.acks(formatCount(record.accepted), formatCount(record.rejected)));
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function ClaimFileItem({ record, onDownload }: ClaimFileItemProps) {
  const acks = acknowledgment(record);
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-4 py-3">
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="text-body">
          {CLAIM_FILE_TEXT.meta(record.file_name, formatCount(record.claims), formatMoney(record.total_cents / 100))}
        </span>
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-footnote text-secondary">
          <StatusDot tone={OUTCOME_TONES[record.outcome]}>{CLAIM_FILE_TEXT.outcomes[record.outcome]}</StatusDot>
          {record.usage === "test" ? <span>{CLAIM_FILE_TEXT.test}</span> : null}
          <span>
            {formatDateTime(record.at)} · {record.by}
          </span>
          {acks ? <span>{acks}</span> : null}
        </span>
        {record.error ? <span className="text-footnote text-bad-text">{sentence(record.error)}</span> : null}
      </span>
      <Button size="sm" onClick={() => onDownload(record)}>
        {CLAIM_FILE_TEXT.download}
      </Button>
    </li>
  );
}

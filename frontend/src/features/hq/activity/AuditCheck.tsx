import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import type { AuditVerification } from "@/lib/api/types";
import { formatCount, formatDateTime } from "@/lib/format";
import { HQ_TEXT } from "../strings";
import { brokenChainLine } from "./activityModel";

const words = HQ_TEXT.activity.check;

interface AuditCheckProps {
  result: AuditVerification | null;
  error: string | null;
}

export function AuditCheck({ result, error }: AuditCheckProps) {
  if (error) return <InlineAlert tone="bad">{error}</InlineAlert>;
  if (!result) return null;
  const broken = result.chains.filter((chain) => !chain.intact);
  const entries = result.chains.reduce((total, chain) => total + chain.checked, 0);
  return (
    <Panel aria-label={words.label}>
      <div className="flex flex-col gap-2 px-4 py-3 text-body">
        {broken.length === 0 ? (
          <StatusDot tone="ok">{words.intact(formatCount(result.chains.length), formatCount(entries))}</StatusDot>
        ) : (
          <StatusDot tone="bad">{words.broken(formatCount(broken.length))}</StatusDot>
        )}
        {broken.length > 0 ? (
          <ul className="m-0 list-none p-0">
            {broken.map((chain) => (
              <li key={`${chain.chain}-${chain.practice_id ?? ""}`}>{brokenChainLine(chain)}</li>
            ))}
          </ul>
        ) : null}
        <span className="text-footnote text-secondary">{words.checkedAt(formatDateTime(result.checked_at))}</span>
      </div>
    </Panel>
  );
}

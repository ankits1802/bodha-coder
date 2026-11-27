import type { ReturnRecord } from "@/lib/api/types";
import { RETURN_REASON_LABELS } from "@/lib/labels";
import { REVIEW_TEXT } from "../strings";
import { HistoryEntry, HistoryList, joinMeta } from "./HistoryEntry";
import { byLabel } from "./HistoryReadings";

const words = REVIEW_TEXT.history;

export function HistoryReturns({ returns }: { returns: ReturnRecord[] }) {
  return (
    <HistoryList>
      {returns.map((record) => (
        <HistoryEntry
          key={`${record.at}-${record.reason}`}
          at={record.at}
          title={<span className="font-medium">{RETURN_REASON_LABELS[record.reason]}</span>}
          meta={joinMeta([record.note, record.flag_reason ? words.flagWas(record.flag_reason) : null, byLabel(record.by, record.role)])}
        />
      ))}
    </HistoryList>
  );
}

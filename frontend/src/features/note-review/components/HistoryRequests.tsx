import type { AddendumRequestView } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { CHANNEL_LABELS } from "@/lib/labels";
import { REVIEW_TEXT } from "../strings";
import { HistoryEntry, HistoryList, joinMeta } from "./HistoryEntry";

export function HistoryRequests({ requests }: { requests: AddendumRequestView[] }) {
  const words = REVIEW_TEXT.questions;
  return (
    <HistoryList>
      {requests.map((request) => (
        <HistoryEntry
          key={request.id}
          at={request.sent_at}
          title={<span className="font-medium">{words.requestStatus[request.status]}</span>}
          meta={joinMeta([
            CHANNEL_LABELS[request.channel],
            request.hold_claim ? words.held : null,
            request.answered_at ? words.answeredOn(formatDateTime(request.answered_at)) : null,
          ])}
        >
          <ol className="m-0 pl-4.5 text-callout">
            {request.questions.map((question) => (
              <li key={question.key}>{question.text}</li>
            ))}
          </ol>
        </HistoryEntry>
      ))}
    </HistoryList>
  );
}

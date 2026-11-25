import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { AddendumRequestView, RequestStatus } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { CHANNEL_LABELS } from "@/lib/labels";
import { REVIEW_TEXT } from "../strings";

const TONES: Record<RequestStatus, StatusTone> = { sent: "warn", answered: "ok", expired: "bad", cancelled: "neutral" };

interface RequestListProps {
  requests: AddendumRequestView[];
  onRemind: (() => void) | null;
  remindPending: boolean;
  remindMessage: string | null;
  onCancel: (() => void) | null;
  cancelPending: boolean;
}

function answerFor(request: AddendumRequestView, key: string): string | null {
  const answer = request.answers?.find((item) => item.key === key);
  if (!answer) return null;
  return [answer.choice === REVIEW_TEXT.questions.other ? null : answer.choice, answer.comment].filter(Boolean).join(" · ");
}

function RequestItem({ request, remind }: { request: AddendumRequestView; remind: ReactNode }) {
  const words = REVIEW_TEXT.questions;
  return (
    <li className="flex flex-col gap-2 border-t border-hairline px-5 py-4 first:border-t-0">
      <span className="flex flex-wrap items-center justify-between gap-2">
        <StatusDot tone={TONES[request.status]}>{words.requestStatus[request.status]}</StatusDot>
        <span className="text-footnote text-secondary">
          {[CHANNEL_LABELS[request.channel], words.sentOn(formatDateTime(request.sent_at)), request.hold_claim ? words.held : null]
            .filter(Boolean)
            .join(" · ")}
        </span>
      </span>
      <ol className="m-0 flex flex-col gap-1 pl-4.5">
        {request.questions.map((question) => (
          <li key={question.key}>
            <span className="font-medium">{question.text}</span>
            {answerFor(request, question.key) ? <span className="block text-secondary">{answerFor(request, question.key)}</span> : null}
          </li>
        ))}
      </ol>
      {request.addendum_text ? <p className="m-0 rounded-field bg-chip px-3.5 py-2.5 whitespace-pre-wrap">{request.addendum_text}</p> : null}
      {request.status === "sent" ? remind : null}
    </li>
  );
}

export function RequestList({ requests, onRemind, remindPending, remindMessage, onCancel, cancelPending }: RequestListProps) {
  if (requests.length === 0) return null;
  const remind = onRemind || onCancel ? (
    <span className="flex flex-wrap items-center gap-3">
      {onRemind ? (
        <Button size="sm" onClick={onRemind} pending={remindPending}>
          {REVIEW_TEXT.questions.remind}
        </Button>
      ) : null}
      {onCancel ? (
        <Button size="sm" variant="plain" onClick={onCancel} pending={cancelPending}>
          {REVIEW_TEXT.questions.cancelRequest}
        </Button>
      ) : null}
      {remindMessage ? <span role="status" className="text-footnote text-secondary">{remindMessage}</span> : null}
    </span>
  ) : null;
  return (
    <section className="border-t border-hairline">
      <h3 className="m-0 px-5 pt-4 font-sans text-subhead font-semibold text-secondary">{REVIEW_TEXT.questions.requests}</h3>
      <ul className="m-0 list-none p-0">
        {requests.map((request) => (
          <RequestItem key={request.id} request={request} remind={remind} />
        ))}
      </ul>
    </section>
  );
}

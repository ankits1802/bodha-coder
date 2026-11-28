"use client";

import { useState } from "react";
import { Pager } from "@/components/ui/Pager";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getIntakeMessages } from "@/lib/api/emailIntake";
import type { IntakeMessage } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { messageSummary, messageTone, refusedReasons } from "./messageOutcomes";
import { EMAIL_INTAKE_TEXT } from "./strings";

export const INTAKE_MESSAGES_KEY = "practice-email-intake-messages";

const words = EMAIL_INTAKE_TEXT;
const REMOTE_TEXT = { loading: words.loading, empty: words.nothingReceived, retry: words.retry };

function IntakeMessageItem({ message }: { message: IntakeMessage }) {
  return (
    <li className="flex flex-col gap-1 border-t border-hairline py-2.5 first:border-t-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="min-w-0 text-body break-all text-label">{message.sender ?? words.unknownSender}</span>
        <span className="text-subhead text-secondary tabular-nums">{formatDateTime(message.received_at)}</span>
      </div>
      <StatusDot tone={messageTone(message)}>{messageSummary(message)}</StatusDot>
      {refusedReasons(message).map((reason) => (
        <span key={reason} className="text-footnote text-secondary">
          {reason}
        </span>
      ))}
    </li>
  );
}

export function IntakeMessages({ version }: { version: number }) {
  const [offset, setOffset] = useState(0);
  const remote = useRemote(`${INTAKE_MESSAGES_KEY}:${version}:${offset}`, () => getIntakeMessages(offset));
  return (
    <div className="flex flex-col gap-2 border-t border-hairline px-4 py-4">
      <span className="text-subhead font-medium text-label">{words.received}</span>
      <RemoteView state={remote.state} text={REMOTE_TEXT} isEmpty={(page) => page.total === 0} onRetry={remote.reload}>
        {(page) => (
          <>
            <ul aria-label={words.received} className="m-0 list-none p-0">
              {page.items.map((message) => (
                <IntakeMessageItem key={message.id} message={message} />
              ))}
            </ul>
            <Pager offset={page.offset} pageSize={page.page_size} shown={page.items.length} total={page.total} text={words.pager} onOffset={setOffset} />
          </>
        )}
      </RemoteView>
    </div>
  );
}

import Link from "next/link";
import { Chevron } from "@/components/ui/Chevron";
import { ToneDot } from "@/components/ui/StatusDot";
import type { InboxEntry } from "@/lib/api/types";
import { formatSince } from "@/lib/format";
import { inboxMeta, inboxSentence, inboxTarget, isUnread } from "../inboxModel";
import { INBOX_TEXT } from "../strings";

interface InboxRowProps {
  entry: InboxEntry;
  onOpen: (entry: InboxEntry) => void;
}

const ROW = "flex items-start gap-3 px-4.5 py-3.5";

function RowBody({ entry }: { entry: InboxEntry }) {
  const unread = isUnread(entry);
  const meta = inboxMeta(entry);
  return (
    <>
      <span className="flex h-6 w-2 flex-none items-center">{unread ? <ToneDot tone="low" /> : null}</span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className={`text-body ${unread ? "font-semibold" : "text-label-soft"}`}>
          {unread ? <span className="sr-only">{`${INBOX_TEXT.unread}: `}</span> : null}
          {inboxSentence(entry)}
        </span>
        {meta ? <span className="truncate text-subhead text-secondary">{meta}</span> : null}
      </span>
      <span className="flex-none pt-0.5 text-subhead whitespace-nowrap text-secondary tabular-nums">{formatSince(entry.created_at)}</span>
    </>
  );
}

export function InboxRow({ entry, onOpen }: InboxRowProps) {
  const target = inboxTarget(entry);
  return (
    <li className="border-t border-hairline first:border-t-0">
      {target ? (
        <Link href={target} onClick={() => onOpen(entry)} className={`${ROW} hover:bg-row-hover`}>
          <RowBody entry={entry} />
          <span className="flex-none self-center">
            <Chevron />
          </span>
        </Link>
      ) : (
        <div className={ROW}>
          <RowBody entry={entry} />
        </div>
      )}
    </li>
  );
}

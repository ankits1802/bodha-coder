import type { ReactNode } from "react";
import { formatDateTime } from "@/lib/format";

interface HistoryEntryProps {
  at: string | null;
  title: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
}

export function HistoryEntry({ at, title, meta, children }: HistoryEntryProps) {
  return (
    <li className="flex flex-wrap gap-x-4 gap-y-1 border-t border-hairline py-2.5 first:border-t-0 first:pt-0">
      <span className="w-28 flex-none text-footnote text-secondary tabular-nums">
        {at ? <time dateTime={at}>{formatDateTime(at)}</time> : null}
      </span>
      <span className="flex min-w-0 flex-[1_1_16rem] flex-col gap-1">
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">{title}</span>
        {meta ? <span className="text-footnote text-secondary">{meta}</span> : null}
        {children}
      </span>
    </li>
  );
}

export function HistoryList({ children }: { children: ReactNode }) {
  return <ul className="m-0 list-none p-0">{children}</ul>;
}

export function joinMeta(parts: (string | null | undefined)[]): string {
  return parts.filter(Boolean).join(" · ");
}

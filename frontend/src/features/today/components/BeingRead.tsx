import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusDot } from "@/components/ui/StatusDot";
import type { BatchProgress } from "@/lib/api/types";
import { formatCalendarDay, formatCount } from "@/lib/format";
import { batchCounts, type BatchCounts } from "../batchProgress";
import { TODAY_TEXT } from "../strings";

interface BeingReadProps {
  batches: BatchProgress[];
  placeNames: Record<string, string>;
  canUpload: boolean;
  canOpenQueue: boolean;
}

function BatchState({ counts, canOpenQueue }: { counts: BatchCounts; canOpenQueue: boolean }) {
  if (counts.failed > 0) {
    return (
      <span className="flex flex-wrap items-center justify-between gap-3">
        <StatusDot tone="bad">{TODAY_TEXT.failed(formatCount(counts.failed))}</StatusDot>
        {canOpenQueue ? (
          <Link href="/queue" className="text-subhead font-medium text-label underline">
            {TODAY_TEXT.openQueue}
          </Link>
        ) : null}
      </span>
    );
  }
  const text = counts.pending === 0 ? TODAY_TEXT.done : TODAY_TEXT.reading(formatCount(counts.pending));
  return <span className="text-footnote text-secondary">{text}</span>;
}

interface BatchRowProps {
  batch: BatchProgress;
  placeNames: Record<string, string>;
  canOpenQueue: boolean;
}

function BatchRow({ batch, placeNames, canOpenQueue }: BatchRowProps) {
  const counts = batchCounts(batch);
  const place = placeNames[batch.place_code] ?? TODAY_TEXT.placeCode(batch.place_code);
  const name = TODAY_TEXT.batchName(batch.provider_name, place, formatCalendarDay(batch.service_date));
  const complete = counts.pending === 0 && counts.failed === 0;
  return (
    <li className="flex flex-col gap-2 px-4.5 py-3.5">
      <span className="flex justify-between gap-3">
        <span className="font-medium">{name}</span>
        <span className="text-secondary tabular-nums">
          {TODAY_TEXT.progress(formatCount(counts.finished), formatCount(counts.total))}
        </span>
      </span>
      <ProgressBar
        label={TODAY_TEXT.progressLabel(name)}
        value={counts.finished}
        max={counts.total}
        tone={complete ? "ok" : "neutral"}
      />
      <BatchState counts={counts} canOpenQueue={canOpenQueue} />
    </li>
  );
}

export function BeingRead({ batches, placeNames, canUpload, canOpenQueue }: BeingReadProps) {
  return (
    <section aria-labelledby="today-being-read" className="flex min-w-0 flex-[2_1_20rem] flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="today-being-read" className="m-0 text-title3 font-semibold tracking-headline">
          {TODAY_TEXT.beingRead}
        </h2>
        {canUpload ? (
          <Link href="/upload" className="text-body text-secondary hover:underline">
            {TODAY_TEXT.uploadMore}
          </Link>
        ) : null}
      </div>
      <Panel as="div">
        {batches.length === 0 ? (
          <EmptyState title={TODAY_TEXT.noBatches} />
        ) : (
          <ul className="m-0 list-none divide-y divide-hairline p-0">
            {batches.map((batch) => (
              <BatchRow key={batch.id} batch={batch} placeNames={placeNames} canOpenQueue={canOpenQueue} />
            ))}
          </ul>
        )}
      </Panel>
    </section>
  );
}

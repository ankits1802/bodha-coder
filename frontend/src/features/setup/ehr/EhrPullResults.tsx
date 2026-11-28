"use client";

import { useState } from "react";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { Pager } from "@/components/ui/Pager";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getEhrDocuments, getEhrPullRuns } from "@/lib/api/ehrConnection";
import type { EhrDocument, EhrPullRun } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { notePath } from "@/lib/paths";
import { documentSummary, documentTone, runSummary, runTone } from "./pullOutcomes";
import { EHR_TEXT } from "./strings";

export const EHR_RUNS_KEY = "practice-ehr-runs";
export const EHR_DOCUMENTS_KEY = "practice-ehr-documents";

const words = EHR_TEXT;
const RUNS_TEXT = { loading: words.loading, empty: words.noRuns, retry: words.retry };
const DOCUMENTS_TEXT = { loading: words.loading, empty: words.noDocuments, retry: words.retry };

function RunItem({ run }: { run: EhrPullRun }) {
  return (
    <li className="flex flex-col gap-1 border-t border-hairline py-2.5 first:border-t-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <StatusDot tone={runTone(run)}>{runSummary(run)}</StatusDot>
        <span className="text-subhead text-secondary tabular-nums">{formatDateTime(run.started_at)}</span>
      </div>
      <span className="text-footnote text-secondary">{words.runCounts(run)}</span>
    </li>
  );
}

function DocumentItem({ document }: { document: EhrDocument }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline py-2.5 first:border-t-0">
      <div className="flex min-w-0 flex-col gap-0.5">
        <StatusDot tone={documentTone(document)}>{documentSummary(document)}</StatusDot>
        <span className="text-footnote break-all text-secondary">{document.document_id}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-subhead text-secondary tabular-nums">{formatDateTime(document.fetched_at)}</span>
        {document.note_id ? (
          <ButtonLink href={notePath(document.note_id)} size="sm" variant="plain">
            {words.openNote}
          </ButtonLink>
        ) : null}
      </div>
    </li>
  );
}

export function EhrPullResults({ version }: { version: number }) {
  const [offset, setOffset] = useState(0);
  const pulls = useRemote(`${EHR_RUNS_KEY}:${version}`, () => getEhrPullRuns(0));
  const fetched = useRemote(`${EHR_DOCUMENTS_KEY}:${version}:${offset}`, () => getEhrDocuments(offset));
  return (
    <>
      <div className="flex flex-col gap-2 border-t border-hairline px-4 py-4">
        <span className="text-subhead font-medium text-label">{words.runs}</span>
        <RemoteView state={pulls.state} text={RUNS_TEXT} isEmpty={(page) => page.total === 0} onRetry={pulls.reload}>
          {(page) => (
            <ul aria-label={words.runs} className="m-0 list-none p-0">
              {page.items.map((run) => (
                <RunItem key={run.id} run={run} />
              ))}
            </ul>
          )}
        </RemoteView>
      </div>
      <div className="flex flex-col gap-2 border-t border-hairline px-4 py-4">
        <span className="text-subhead font-medium text-label">{words.documents}</span>
        <RemoteView state={fetched.state} text={DOCUMENTS_TEXT} isEmpty={(page) => page.total === 0} onRetry={fetched.reload}>
          {(page) => (
            <>
              <ul aria-label={words.documents} className="m-0 list-none p-0">
                {page.items.map((item) => (
                  <DocumentItem key={item.id} document={item} />
                ))}
              </ul>
              <Pager offset={page.offset} pageSize={page.page_size} shown={page.items.length} total={page.total} text={words.pager} onOffset={setOffset} />
            </>
          )}
        </RemoteView>
      </div>
    </>
  );
}

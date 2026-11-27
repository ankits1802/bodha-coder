"use client";

import { Button } from "@/components/ui/Button";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { downloadExport, getExports } from "@/lib/api/billing";
import type { ExportRecord } from "@/lib/api/types";
import { saveFile } from "@/lib/download";
import { formatCount, formatDateTime } from "@/lib/format";
import { BILLING_TEXT } from "../strings";

const REMOTE_TEXT = { loading: BILLING_TEXT.loading, empty: BILLING_TEXT.filesEmpty, retry: BILLING_TEXT.retry };

export function ExportFiles() {
  const exports = useRemote("billing-exports", () => getExports(0));
  const download = useAction(downloadExport);

  async function save(record: ExportRecord): Promise<void> {
    const outcome = await download.run(record.id);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? record.file_name);
  }

  return (
    <Panel aria-label={BILLING_TEXT.files}>
      <PanelHeader title={BILLING_TEXT.files} />
      <RemoteView state={exports.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={exports.reload}>
        {(data) => (
          <ul className="m-0 list-none p-0">
            {data.items.map((record) => (
              <li key={record.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-4 py-3">
                <span className="flex min-w-0 flex-col">
                  <span className="text-body">{BILLING_TEXT.fileMeta(record.file_name, formatCount(record.notes))}</span>
                  <span className="text-footnote text-secondary">
                    {formatDateTime(record.at)} · {record.by} · {record.sha256.slice(0, 12)}
                  </span>
                </span>
                <Button size="sm" onClick={() => void save(record)}>
                  {BILLING_TEXT.download}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </RemoteView>
      {download.error ? (
        <p role="alert" className="m-0 px-4 pb-3 text-footnote text-bad-text">
          {download.error}
        </p>
      ) : null}
    </Panel>
  );
}

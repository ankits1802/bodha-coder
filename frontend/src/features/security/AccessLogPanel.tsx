"use client";

import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { exportAccessLog, getAccessLog } from "@/lib/api/practice";
import { saveFile } from "@/lib/download";
import { accessLogFilters, filterChanges, filtersKey } from "./accessLog";
import { AccessLogFilterBar } from "./AccessLogFilterBar";
import { AccessLogTable } from "./AccessLogTable";
import { SECURITY_TEXT } from "./strings";

const words = SECURITY_TEXT.log;

export function AccessLogPanel() {
  const query = useQueryParams();
  const today = usePracticeToday();
  const filters = accessLogFilters(query.get, today);
  const offset = offsetFrom(query.get("offset"));
  const log = useRemote(filtersKey(filters, offset), () => getAccessLog(filters, offset));
  const download = useAction(exportAccessLog);
  const page = log.state.status === "success" ? log.state.data : null;

  async function exportCsv(): Promise<void> {
    const outcome = await download.run(filters);
    if (outcome.ok) saveFile(outcome.value.blob, outcome.value.fileName ?? words.fileName(filters.start, filters.end));
  }

  return (
    <Panel aria-label={words.title}>
      <PanelHeader
        title={words.title}
        actions={
          <Button size="sm" disabled={!page || page.total === 0} pending={download.pending} onClick={() => void exportCsv()}>
            {words.export}
          </Button>
        }
      />
      <AccessLogFilterBar
        filters={filters}
        today={today}
        people={page?.people ?? []}
        actions={page?.actions ?? []}
        onChange={(changes) => query.update(filterChanges(changes))}
      />
      {download.error ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{download.error}</InlineAlert>
        </div>
      ) : null}
      <RemoteView
        state={log.state}
        text={{ loading: words.loading, empty: words.empty, retry: words.retry }}
        isEmpty={(data) => data.items.length === 0 && data.offset === 0}
        onRetry={log.reload}
      >
        {(data) => (
          <>
            <AccessLogTable entries={data.items} />
            <div className="px-4 py-3 empty:hidden">
              <Pager
                offset={data.offset}
                pageSize={data.page_size}
                shown={data.items.length}
                total={data.total}
                text={SHARED_TEXT.pager}
                onOffset={(next) => query.update({ offset: next > 0 ? String(next) : null })}
              />
            </div>
          </>
        )}
      </RemoteView>
    </Panel>
  );
}

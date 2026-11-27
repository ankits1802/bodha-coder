"use client";

import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { DatePicker } from "@/components/ui/DatePicker";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { Select } from "@/components/ui/Select";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { getAccessLog } from "@/lib/api/practice";
import { getTeam } from "@/lib/api/team";
import { isIsoDate } from "@/lib/dates";
import { saveFile } from "@/lib/download";
import { accessLogCsv } from "./accessLog";
import { AccessLogTable } from "./AccessLogTable";
import { SECURITY_TEXT } from "./strings";

export function AccessLogPanel() {
  const query = useQueryParams();
  const today = usePracticeToday();
  const requested = query.get("day");
  const day = requested && isIsoDate(requested) ? requested : today;
  const person = query.get("user");
  const offset = offsetFrom(query.get("offset"));
  const team = useRemote("security-team", getTeam);
  const log = useRemote(`access-log:${day}:${person ?? ""}:${offset}`, () => getAccessLog(day, person, offset));
  const words = SECURITY_TEXT.log;
  const members = team.state.status === "success" ? team.state.data.members : [];
  const page = log.state.status === "success" ? log.state.data : null;
  const entries = page ? page.items : [];

  function exportCsv(): void {
    saveFile(new Blob([accessLogCsv(entries)], { type: "text/csv" }), words.fileName(day));
  }

  const filters = (
    <>
      <Select
        variant="filter"
        label={words.person}
        value={person ?? ""}
        options={[{ value: "", label: words.anyone }, ...members.map((member) => ({ value: member.id, label: member.name }))]}
        onChange={(user) => query.update({ user: user || null, offset: null })}
      />
      <DatePicker
        variant="filter"
        label={words.day}
        value={day}
        max={today}
        today={today}
        onChange={(value) => {
          if (value) query.update({ day: value === today ? null : value, offset: null });
        }}
      />
      <Button size="sm" disabled={entries.length === 0} onClick={exportCsv}>
        {words.export}
      </Button>
    </>
  );

  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} actions={filters} />
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

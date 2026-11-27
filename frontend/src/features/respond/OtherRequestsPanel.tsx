import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { formatCalendarDay, formatDateTime } from "@/lib/format";
import { RESPOND_TEXT } from "./strings";
import type { OtherRequests } from "./useOtherRequests";

export function OtherRequestsPanel({ others }: { others: OtherRequests }) {
  const state = others.remote.state;
  if (state.status === "loading") return null;
  if (state.status === "error") {
    return (
      <Panel aria-label={RESPOND_TEXT.others}>
        <ErrorState message={state.error} retryLabel={RESPOND_TEXT.retry} onRetry={others.remote.reload} />
      </Panel>
    );
  }
  if (state.data.length === 0) return null;
  return (
    <Panel aria-label={RESPOND_TEXT.others}>
      <PanelHeader title={RESPOND_TEXT.others} />
      {others.error ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{others.error}</InlineAlert>
        </div>
      ) : null}
      <ul className="m-0 flex list-none flex-col p-0">
        {state.data.map((item) => {
          const patient = item.patient_name ?? RESPOND_TEXT.patientUnknown;
          return (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-4 py-3">
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-body font-medium">{patient}</span>
                <span className="text-subhead text-secondary">
                  {RESPOND_TEXT.otherMeta(formatCalendarDay(item.service_date), item.questions, formatDateTime(item.sent_at))}
                </span>
              </span>
              <Button
                size="sm"
                aria-label={RESPOND_TEXT.openOther(patient)}
                pending={others.openingId === item.id}
                disabled={others.openingId !== null}
                onClick={() => others.open(item.id)}
              >
                {RESPOND_TEXT.open}
              </Button>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

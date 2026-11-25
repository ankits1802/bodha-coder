"use client";

import { noteStatus } from "@/components/shared/noteStatus";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot } from "@/components/ui/StatusDot";
import { useRemote } from "@/hooks/useRemote";
import { getNote } from "@/lib/api/notes";
import { placeName, type PlaceNames } from "@/hooks/usePlaceNames";
import type { ComplianceRow } from "@/lib/api/types";
import { formatCalendarDay, formatDueIn } from "@/lib/format";
import { caseFacts } from "../complianceKinds";
import { COMPLIANCE_TEXT } from "../strings";
import { CaseActions } from "./CaseActions";
import { CaseFactsView } from "./CaseFactsView";

const REMOTE_TEXT = { loading: COMPLIANCE_TEXT.loadingCase, empty: COMPLIANCE_TEXT.emptyKind, retry: COMPLIANCE_TEXT.retry };

interface FeaturedCaseProps {
  row: ComplianceRow;
  placeNames: PlaceNames;
  canDecide: boolean;
  onDecided: (message: string) => void;
}

export function FeaturedCase({ row, placeNames, canDecide, onDecided }: FeaturedCaseProps) {
  const detail = useRemote(`compliance-case:${row.id}`, () => getNote(row.id));
  const status = noteStatus(row);
  const facts = detail.state.status === "success" ? caseFacts(detail.state.data, row) : null;
  return (
    <Panel as="article" aria-labelledby={`case-${row.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-hairline px-5 py-4.5">
        <span className="flex flex-col gap-0.5">
          <h2 id={`case-${row.id}`} className="m-0 font-sans text-headline font-semibold tracking-headline">
            {row.patient_name ?? row.file_name}
          </h2>
          <span className="text-subhead text-secondary">
            {SHARED_TEXT.noteRow.meta(row.provider_name, placeName(placeNames, row.place_code) ?? row.place_code, formatCalendarDay(row.service_date))}
          </span>
        </span>
        <span className="flex items-center gap-4.5">
          <StatusDot tone={status.tone}>{status.label}</StatusDot>
          <span className="text-secondary tabular-nums">
            <span className="sr-only">{SHARED_TEXT.noteRow.dueIn} </span>
            {formatDueIn(row.due_at).text}
          </span>
        </span>
      </div>
      <RemoteView state={detail.state} text={REMOTE_TEXT} onRetry={detail.reload}>
        {(note) => <CaseFactsView facts={caseFacts(note, row)} />}
      </RemoteView>
      <CaseActions noteId={row.id} facts={facts} canDecide={canDecide} onDecided={onDecided} />
    </Panel>
  );
}

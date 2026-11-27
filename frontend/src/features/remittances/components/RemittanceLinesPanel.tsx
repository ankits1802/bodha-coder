"use client";

import { useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useRemote } from "@/hooks/useRemote";
import { getRemittance } from "@/lib/api/remittances";
import type { RemittanceCounts, RemittanceFilter, RemittanceLine } from "@/lib/api/types";
import { REMITTANCE_FILTERS } from "../remittanceModel";
import { REMITTANCE_TEXT } from "../strings";
import { AppealDialog } from "./AppealDialog";
import { RemittanceLines } from "./RemittanceLines";

interface RemittanceLinesPanelProps {
  remittanceId: string;
  filter: RemittanceFilter;
  onFilter: (filter: RemittanceFilter) => void;
}

const REMOTE_TEXT = { loading: REMITTANCE_TEXT.loadingLines, empty: REMITTANCE_TEXT.noLines, retry: REMITTANCE_TEXT.retry };

function segmentsFor(counts: RemittanceCounts | null) {
  const total = counts ? Object.values(counts).reduce((sum, count) => sum + (count ?? 0), 0) : undefined;
  return REMITTANCE_FILTERS.map((value) => ({
    value,
    label: REMITTANCE_TEXT.filters[value],
    count: counts ? (value === "all" ? total : (counts[value] ?? 0)) : undefined,
  }));
}

export function RemittanceLinesPanel({ remittanceId, filter, onFilter }: RemittanceLinesPanelProps) {
  const detail = useRemote(`remittance:${remittanceId}:${filter}`, () => getRemittance(remittanceId, filter));
  const [drafting, setDrafting] = useState<RemittanceLine | null>(null);
  const loaded = detail.state.status === "success" ? detail.state.data : null;
  const title = loaded ? REMITTANCE_TEXT.fileTitle(loaded.remittance.file_name, loaded.remittance.payer) : REMITTANCE_TEXT.linesLabel;

  return (
    <Panel>
      <PanelHeader
        title={title}
        actions={
          <SegmentedControl
            label={REMITTANCE_TEXT.filterLabel}
            value={filter}
            segments={segmentsFor(loaded ? loaded.remittance.counts : null)}
            onChange={onFilter}
            size="sm"
          />
        }
      />
      <RemoteView state={detail.state} text={REMOTE_TEXT} isEmpty={(data) => data.lines.length === 0} onRetry={detail.reload}>
        {(data) => (
          <RemittanceLines lines={data.lines} onDraft={(lineId) => setDrafting(data.lines.find((line) => line.id === lineId) ?? null)} />
        )}
      </RemoteView>
      <AppealDialog line={drafting} onClose={() => setDrafting(null)} />
    </Panel>
  );
}

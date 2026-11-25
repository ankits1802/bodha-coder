"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getBilling } from "@/lib/api/billing";
import type { BillingRow, BillingShow } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { BILLING_SHOWS, isBillingShow } from "./billingRows";
import { BillingStats } from "./components/BillingStats";
import { BillingTable } from "./components/BillingTable";
import { BILLING_TEXT } from "./strings";
import { useExport, type ExportAction } from "./useExport";

const REMOTE_TEXT = { loading: BILLING_TEXT.loading, empty: BILLING_TEXT.empty, retry: BILLING_TEXT.retry };
const SEGMENTS = BILLING_SHOWS.map((value) => ({ value, label: BILLING_TEXT.show[value] }));

function ExportButton({ show, rows, exporter }: { show: BillingShow; rows: BillingRow[] | null; exporter: ExportAction }) {
  if (show !== "ready" || !rows || rows.length === 0) return null;
  return (
    <Button variant="primary" pending={exporter.pending} onClick={() => void exporter.exportAll(rows.length)}>
      {BILLING_TEXT.export(formatCount(rows.length))}
    </Button>
  );
}

function BillingContent() {
  const params = useQueryParams();
  const showParam = params.get("show");
  const show: BillingShow = isBillingShow(showParam) ? showParam : "ready";
  const billing = useRemote(`billing:${show}`, () => getBilling(show));
  const exporter = useExport(billing.reload);
  const rows = billing.state.status === "success" ? billing.state.data.items : null;
  const filter = (
    <div className="self-start">
      <SegmentedControl
        label={BILLING_TEXT.showLabel}
        value={show}
        segments={SEGMENTS}
        onChange={(value) => params.update({ show: value === "ready" ? null : value })}
      />
    </div>
  );

  return (
    <>
      <PageHeader
        title={BILLING_TEXT.title}
        subtitle={rows ? BILLING_TEXT.subtitle(formatCount(rows.length)) : undefined}
        actions={<ExportButton show={show} rows={rows} exporter={exporter} />}
      />
      {exporter.notice ? <InlineAlert tone="ok">{exporter.notice}</InlineAlert> : null}
      {exporter.error ? <InlineAlert tone="bad">{exporter.error}</InlineAlert> : null}
      {rows && rows.length > 0 ? null : filter}
      <RemoteView state={billing.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0} onRetry={billing.reload}>
        {(data) => (
          <>
            <BillingStats rows={data.items} />
            {filter}
            <BillingTable rows={data.items} />
          </>
        )}
      </RemoteView>
    </>
  );
}

export function BillingScreen() {
  const { user } = useSession();
  return <AreaGuard area="billing">{user ? <BillingContent /> : null}</AreaGuard>;
}

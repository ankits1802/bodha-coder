"use client";

import { AreaGuard } from "@/components/shared/AreaGuard";
import { SHARED_TEXT } from "@/components/shared/strings";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getBilling } from "@/lib/api/billing";
import type { BillingList, BillingShow } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { BILLING_SHOWS, isBillingShow } from "./billingRows";
import { BillingStats } from "./components/BillingStats";
import { BillingTable } from "./components/BillingTable";
import { BILLING_TEXT } from "./strings";
import { useExport, type ExportAction } from "./useExport";

const REMOTE_TEXT = { loading: BILLING_TEXT.loading, empty: BILLING_TEXT.empty, retry: BILLING_TEXT.retry };
const SEGMENTS = BILLING_SHOWS.map((value) => ({ value, label: BILLING_TEXT.show[value] }));

function ExportButton({ show, page, exporter }: { show: BillingShow; page: BillingList | null; exporter: ExportAction }) {
  if (!page || page.items.length === 0 || show === "all") return null;
  if (show === "exported") {
    const rows = page.items;
    return (
      <Button pending={exporter.pending} onClick={() => void exporter.downloadAgain(rows.map((row) => row.id))}>
        {BILLING_TEXT.downloadAgain(formatCount(rows.length))}
      </Button>
    );
  }
  const visits = Math.min(page.total, page.limit);
  return (
    <Button variant="primary" pending={exporter.pending} onClick={() => void exporter.exportAll(visits)}>
      {BILLING_TEXT.export(formatCount(visits))}
    </Button>
  );
}

function BillingContent() {
  const params = useQueryParams();
  const showParam = params.get("show");
  const show: BillingShow = isBillingShow(showParam) ? showParam : "ready";
  const offset = offsetFrom(params.get("offset"));
  const billing = useRemote(`billing:${show}:${offset}`, () => getBilling(show, offset));
  const exporter = useExport(billing.reload);
  const page = billing.state.status === "success" ? billing.state.data : null;
  const rows = page ? page.items : null;
  const filter = (
    <div className="self-start">
      <SegmentedControl
        label={BILLING_TEXT.showLabel}
        value={show}
        segments={SEGMENTS}
        onChange={(value) => params.update({ show: value === "ready" ? null : value, offset: null })}
      />
    </div>
  );

  return (
    <>
      <PageHeader
        title={BILLING_TEXT.title}
        subtitle={page ? BILLING_TEXT.subtitle(formatCount(page.total)) : undefined}
        actions={<ExportButton show={show} page={page} exporter={exporter} />}
      />
      {exporter.notice ? <InlineAlert tone="ok">{exporter.notice}</InlineAlert> : null}
      {exporter.error ? <InlineAlert tone="bad">{exporter.error}</InlineAlert> : null}
      {rows && rows.length > 0 ? null : filter}
      <RemoteView state={billing.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0 && data.offset === 0} onRetry={billing.reload}>
        {(data) => (
          <>
            <BillingStats billing={data} />
            {filter}
            <BillingTable rows={data.items} />
            <Pager
              offset={data.offset}
              pageSize={data.page_size}
              shown={data.items.length}
              total={data.total}
              text={SHARED_TEXT.pager}
              onOffset={(next) => params.update({ offset: next > 0 ? String(next) : null })}
            />
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

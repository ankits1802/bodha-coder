"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { SHARED_TEXT } from "@/components/shared/strings";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { useUsageTask } from "@/hooks/useUsageTask";
import { getBilling } from "@/lib/api/billing";
import type { BillingShow } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { BILLING_SHOWS, isBillingShow } from "./billingRows";
import { BillingStats } from "./components/BillingStats";
import { BillingTable } from "./components/BillingTable";
import { ExportClaimLines } from "./components/ExportClaimLines";
import { ExportFiles } from "./components/ExportFiles";
import { BILLING_TEXT } from "./strings";

const REMOTE_TEXT = { loading: BILLING_TEXT.loading, empty: BILLING_TEXT.empty, retry: BILLING_TEXT.retry };
const SEGMENTS = BILLING_SHOWS.map((value) => ({ value, label: BILLING_TEXT.show[value] }));

function BillingContent() {
  const params = useQueryParams();
  const showParam = params.get("show");
  const show: BillingShow = isBillingShow(showParam) ? showParam : "ready";
  const offset = offsetFrom(params.get("offset"));
  const billing = useRemote(`billing:${show}:${offset}`, () => getBilling(show, offset));
  const [notice, setNotice] = useState<string | null>(null);
  const usage = useUsageTask("billing_export");
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
        actions={
          show === "ready" && page && page.items.length > 0 ? (
            <ExportClaimLines
              visits={Math.min(page.total, page.limit)}
              onExported={(message) => {
                usage.complete();
                setNotice(message);
                billing.reload();
              }}
            />
          ) : null
        }
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
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
      {show === "exported" ? <ExportFiles /> : null}
    </>
  );
}

export function BillingScreen() {
  const { user } = useSession();
  return <AreaGuard area="billing">{user ? <BillingContent /> : null}</AreaGuard>;
}

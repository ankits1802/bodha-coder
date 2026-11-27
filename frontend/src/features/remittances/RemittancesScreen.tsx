"use client";

import { useState } from "react";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { SHARED_TEXT } from "@/components/shared/strings";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getRemittances, uploadRemittance } from "@/lib/api/remittances";
import type { RemittanceFilter, RemittanceUpload } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { AppealWindows } from "./components/AppealWindows";
import { RemittanceFiles } from "./components/RemittanceFiles";
import { RemittanceLinesPanel } from "./components/RemittanceLinesPanel";
import { UploadRemittanceButton } from "./components/UploadRemittanceButton";
import { isRemittanceFilter } from "./remittanceModel";
import { REMITTANCE_TEXT } from "./strings";

const REMOTE_TEXT = { loading: REMITTANCE_TEXT.loading, empty: REMITTANCE_TEXT.empty, retry: REMITTANCE_TEXT.retry };

function lineTotal(result: RemittanceUpload): number {
  return Object.values(result.counts).reduce((sum, count) => sum + (count ?? 0), 0);
}

function RemittancesContent({ canSetWindows }: { canSetWindows: boolean }) {
  const params = useQueryParams();
  const offset = offsetFrom(params.get("offset"));
  const statusParam = params.get("status");
  const filter: RemittanceFilter = isRemittanceFilter(statusParam) ? statusParam : "all";
  const files = useRemote(`remittances:${offset}`, () => getRemittances(offset));
  const upload = useAction(uploadRemittance);
  const [notice, setNotice] = useState<string | null>(null);
  const page = files.state.status === "success" ? files.state.data : null;
  const selected = params.get("file") ?? page?.items[0]?.id ?? null;

  function uploaded(result: RemittanceUpload): void {
    setNotice(REMITTANCE_TEXT.uploaded(formatCount(lineTotal(result))));
    params.update({ file: result.ids[0] ?? null, status: null, offset: null });
    files.reload();
  }

  return (
    <>
      <PageHeader
        title={REMITTANCE_TEXT.title}
        subtitle={page ? REMITTANCE_TEXT.subtitle(formatCount(page.total)) : undefined}
        actions={<UploadRemittanceButton upload={upload} onUploaded={uploaded} />}
      />
      {notice ? <InlineAlert tone="ok">{notice}</InlineAlert> : null}
      {upload.error ? <InlineAlert tone="bad">{upload.error}</InlineAlert> : null}
      <RemoteView state={files.state} text={REMOTE_TEXT} isEmpty={(data) => data.items.length === 0 && data.offset === 0} onRetry={files.reload}>
        {(data) => (
          <>
            <RemittanceFiles files={data.items} selectedId={selected} onSelect={(id) => params.update({ file: id, status: null })} />
            <Pager
              offset={data.offset}
              pageSize={data.page_size}
              shown={data.items.length}
              total={data.total}
              text={SHARED_TEXT.pager}
              onOffset={(next) => params.update({ offset: next > 0 ? String(next) : null, file: null })}
            />
            {selected ? (
              <RemittanceLinesPanel
                key={selected}
                remittanceId={selected}
                filter={filter}
                onFilter={(value) => params.update({ status: value === "all" ? null : value })}
              />
            ) : null}
          </>
        )}
      </RemoteView>
      {canSetWindows ? <AppealWindows /> : null}
    </>
  );
}

export function RemittancesScreen() {
  const { user } = useSession();
  return <AreaGuard area="billing">{user ? <RemittancesContent canSetWindows={canUse(user.role, "setup")} /> : null}</AreaGuard>;
}

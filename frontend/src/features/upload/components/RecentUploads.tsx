"use client";

import { SHARED_TEXT } from "@/components/shared/strings";
import { Pager, offsetFrom } from "@/components/ui/Pager";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { usePlaceNames } from "@/hooks/usePlaceNames";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import { getUploadHistory } from "@/lib/api/uploads";
import { canReach } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { UPLOAD_TEXT } from "../strings";
import { UploadHistoryTable } from "./UploadHistoryTable";

const words = UPLOAD_TEXT.history;
const REMOTE_TEXT = { loading: words.loading, empty: words.empty, retry: words.retry };

export function RecentUploads({ refresh }: { refresh: number }) {
  const { user } = useSession();
  const query = useQueryParams();
  const offset = offsetFrom(query.get("offset"));
  const history = useRemote(`upload-history:${offset}:${refresh}`, () => getUploadHistory(offset));
  const placeNames = usePlaceNames();
  const page = history.state.status === "success" ? history.state.data : null;
  const pager = page ? (
    <Pager
      offset={page.offset}
      pageSize={page.page_size}
      shown={page.items.length}
      total={page.total}
      text={SHARED_TEXT.pager}
      onOffset={(next) => query.update({ offset: next > 0 ? String(next) : null })}
    />
  ) : null;

  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} actions={pager} />
      <RemoteView
        state={history.state}
        text={REMOTE_TEXT}
        isEmpty={(data) => data.items.length === 0 && data.offset === 0}
        onRetry={history.reload}
      >
        {(data) => <UploadHistoryTable batches={data.items} placeNames={placeNames} linked={canReach(user, "queue")} />}
      </RemoteView>
    </Panel>
  );
}

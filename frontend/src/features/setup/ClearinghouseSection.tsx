"use client";

import { showToast } from "@/components/shared/toast/toastStore";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getClearinghouse } from "@/lib/api/clearinghouse";
import type { ClearinghouseView } from "@/lib/api/types";
import { ClearinghouseForm } from "./ClearinghouseForm";
import { CLEARINGHOUSE_TEXT } from "./strings";

const REMOTE_TEXT = { loading: CLEARINGHOUSE_TEXT.loading, empty: CLEARINGHOUSE_TEXT.title, retry: CLEARINGHOUSE_TEXT.retry };

export function ClearinghouseSection() {
  const remote = useRemote("setup-clearinghouse", getClearinghouse);

  function saved(view: ClearinghouseView): void {
    remote.replace(view);
    showToast(CLEARINGHOUSE_TEXT.saved);
  }

  return (
    <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
      {(view) => (
        <ClearinghouseForm
          key={view.connection ? `${view.connection.id}` : "new"}
          view={view}
          onSaved={saved}
          onRemoved={remote.replace}
        />
      )}
    </RemoteView>
  );
}

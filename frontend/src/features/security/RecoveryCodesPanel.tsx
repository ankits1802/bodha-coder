"use client";

import { useState } from "react";
import { RecoveryCodeList } from "@/components/shared/RecoveryCodeList";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getRecoveryCodeStatus, replaceRecoveryCodes } from "@/lib/api/account";
import { NewCodesForm } from "./NewCodesForm";
import { SECURITY_TEXT } from "./strings";

export function RecoveryCodesPanel() {
  const words = SECURITY_TEXT.recovery;
  const status = useRemote("recovery-code-status", getRecoveryCodeStatus);
  const replace = useAction(replaceRecoveryCodes);
  const [fresh, setFresh] = useState<string[] | null>(null);

  async function submit(code: string): Promise<boolean> {
    const outcome = await replace.run(code);
    if (!outcome.ok) return false;
    setFresh(outcome.value.codes);
    status.reload();
    return true;
  }

  if (status.state.status === "success" && !status.state.data.enabled) return null;
  return (
    <Panel aria-label={words.title} className="max-w-180">
      <PanelHeader title={words.title} />
      <RemoteView
        state={status.state}
        text={{ loading: words.loading, empty: words.title, retry: words.retry }}
        onRetry={status.reload}
      >
        {(data) => (
          <div className="flex flex-col gap-4 border-t border-hairline px-4.5 py-4">
            <div className="flex items-center justify-between gap-4 text-body">
              <span>{words.remaining}</span>
              <span className="text-secondary tabular-nums">{data.remaining}</span>
            </div>
            {fresh ? <RecoveryCodeList codes={fresh} /> : null}
            <NewCodesForm pending={replace.pending} error={replace.error} onSubmit={submit} />
          </div>
        )}
      </RemoteView>
    </Panel>
  );
}

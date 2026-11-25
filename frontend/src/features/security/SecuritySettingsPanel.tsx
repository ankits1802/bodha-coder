"use client";

import { Panel } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useRemote } from "@/hooks/useRemote";
import { getSetup } from "@/lib/api/practice";
import { SecurityForm } from "./SecurityForm";
import { SECURITY_TEXT } from "./strings";

export function SecuritySettingsPanel() {
  const remote = useRemote("security-settings", getSetup);
  return (
    <Panel aria-label={SECURITY_TEXT.settingsLabel} className="max-w-180">
      <RemoteView
        state={remote.state}
        text={{ loading: SECURITY_TEXT.loading, empty: SECURITY_TEXT.empty, retry: SECURITY_TEXT.retry }}
        isEmpty={(data) => data.security === null}
        onRetry={remote.reload}
      >
        {(data) =>
          data.security ? <SecurityForm settings={data.security} onSaved={remote.reload} /> : null
        }
      </RemoteView>
    </Panel>
  );
}

"use client";

import { useCallback, useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { usePracticeToday } from "@/hooks/usePracticeToday";
import { useRemote } from "@/hooks/useRemote";
import { getEhrConnection } from "@/lib/api/ehrConnection";
import type { EhrConnection, EhrStatus } from "@/lib/api/types";
import { EhrActions } from "./EhrActions";
import { EhrPullResults } from "./EhrPullResults";
import { EhrRegistration } from "./EhrRegistration";
import { EhrSettingsForm } from "./EhrSettingsForm";
import { EHR_TEXT } from "./strings";

export const EHR_CONNECTION_KEY = "practice-ehr-connection";

const words = EHR_TEXT;
const REMOTE_TEXT = { loading: words.loading, empty: words.loading, retry: words.retry };
const TONES: Record<EhrStatus, StatusTone> = {
  unavailable: "neutral",
  off: "neutral",
  incomplete: "warn",
  paused: "warn",
  pulling: "ok",
};

function EhrConnectionBody({ view, onChange }: { view: EhrConnection; onChange: (next: EhrConnection) => void }) {
  const today = usePracticeToday();
  const [version, setVersion] = useState(0);
  const changed = useCallback(
    (next: EhrConnection) => {
      onChange(next);
      setVersion((value) => value + 1);
    },
    [onChange],
  );
  return (
    <>
      <div className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4">
        <span className="text-subhead font-medium text-label">{words.status}</span>
        <StatusDot tone={TONES[view.status]}>{words.statuses[view.status]}</StatusDot>
      </div>
      {view.available ? (
        <>
          <EhrRegistration view={view} onChange={changed} />
          <EhrSettingsForm view={view} today={today} onSaved={changed} />
          <EhrActions view={view} onChange={changed} />
          <EhrPullResults version={version} />
        </>
      ) : null}
    </>
  );
}

export function EhrConnectionPanel() {
  const remote = useRemote(EHR_CONNECTION_KEY, getEhrConnection);
  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} />
      <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
        {(view) => <EhrConnectionBody view={view} onChange={remote.replace} />}
      </RemoteView>
    </Panel>
  );
}

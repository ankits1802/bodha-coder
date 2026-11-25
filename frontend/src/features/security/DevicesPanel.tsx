"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getSignedInDevices, signOutDevice, signOutOtherDevices } from "@/lib/api/account";
import type { SignedInDevice } from "@/lib/api/types";
import { DeviceList } from "./DeviceList";
import { SECURITY_TEXT } from "./strings";

export function DevicesPanel() {
  const words = SECURITY_TEXT.signedIn;
  const remote = useRemote("signed-in-devices", getSignedInDevices);
  const [busyId, setBusyId] = useState<string | null>(null);
  const one = useAction(signOutDevice);
  const others = useAction(signOutOtherDevices);
  const devices = remote.state.status === "success" ? remote.state.data : [];
  const hasOthers = devices.some((device) => !device.current);
  const failure = one.error ?? others.error;

  async function signOutOne(device: SignedInDevice): Promise<void> {
    setBusyId(device.id);
    const outcome = await one.run(device.id);
    setBusyId(null);
    if (outcome.ok) remote.reload();
  }

  async function signOutOthers(): Promise<void> {
    const outcome = await others.run();
    if (outcome.ok) remote.reload();
  }

  const action = (
    <Button size="sm" disabled={!hasOthers} pending={others.pending} onClick={() => void signOutOthers()}>
      {words.signOutOthers}
    </Button>
  );

  return (
    <Panel aria-label={words.title} className="max-w-180">
      <PanelHeader title={words.title} actions={action} />
      {failure ? (
        <div className="px-4.5 pb-3">
          <InlineAlert tone="bad">{failure}</InlineAlert>
        </div>
      ) : null}
      <RemoteView
        state={remote.state}
        text={{ loading: words.loading, empty: words.empty, retry: words.retry }}
        isEmpty={(data) => data.length === 0}
        onRetry={remote.reload}
      >
        {(data) => <DeviceList devices={data} busyId={busyId} onSignOut={(device) => void signOutOne(device)} />}
      </RemoteView>
    </Panel>
  );
}

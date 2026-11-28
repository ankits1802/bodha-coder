"use client";

import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import type { DomainScope } from "@/lib/api/domains";
import { getSso, setUpSso, ssoScopeKey } from "@/lib/api/sso";
import { SsoForm } from "./SsoForm";
import { SSO_TEXT } from "./strings";

const TEXT = { loading: SSO_TEXT.loading, empty: SSO_TEXT.loading, retry: SSO_TEXT.retry };

export function SingleSignOn({ scope }: { scope: DomainScope }) {
  const remote = useRemote(ssoScopeKey(scope), () => getSso(scope));
  const setUp = useAction(setUpSso);

  async function begin(): Promise<void> {
    const outcome = await setUp.run(scope);
    if (outcome.ok) remote.replace(outcome.value);
  }

  return (
    <Panel aria-label={SSO_TEXT.title} className="max-w-180">
      <PanelHeader title={SSO_TEXT.title} />
      <RemoteView state={remote.state} text={TEXT} onRetry={remote.reload}>
        {(settings) =>
          settings.connection ? (
            <SsoForm
              key={settings.connection.id}
              scope={scope}
              settings={settings}
              connection={settings.connection}
              onChanged={remote.replace}
            />
          ) : (
            <div className="flex flex-col gap-3 px-4 pb-4">
              <Button className="self-start" pending={setUp.pending} onClick={() => void begin()}>
                {SSO_TEXT.setUp}
              </Button>
              {setUp.error ? <InlineAlert tone="bad">{setUp.error}</InlineAlert> : null}
            </div>
          )
        }
      </RemoteView>
    </Panel>
  );
}

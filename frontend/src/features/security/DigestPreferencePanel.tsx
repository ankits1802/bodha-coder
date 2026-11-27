"use client";

import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getPreferences, savePreferences } from "@/lib/api/account";
import { canUse } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";

const DIGEST_TEXT = {
  title: "Email",
  summary: "Email me a daily summary",
  loading: "Loading email settings",
  retry: "Try again",
} as const;

const REMOTE_TEXT = { loading: DIGEST_TEXT.loading, empty: "", retry: DIGEST_TEXT.retry };

function DigestToggle() {
  const remote = useRemote("preferences", getPreferences);
  const save = useAction(savePreferences);

  async function change(checked: boolean): Promise<void> {
    const outcome = await save.run({ notify_digest: checked });
    if (outcome.ok) remote.replace(outcome.value);
  }

  return (
    <Panel aria-label={DIGEST_TEXT.title} className="max-w-180">
      <PanelHeader title={DIGEST_TEXT.title} />
      <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
        {(preferences) => (
          <div className="flex flex-col gap-3 px-4.5 pb-4">
            <div className="flex items-center justify-between gap-4">
              <span aria-hidden="true" className="text-body">
                {DIGEST_TEXT.summary}
              </span>
              <Toggle
                label={DIGEST_TEXT.summary}
                checked={preferences.notify_digest}
                disabled={save.pending}
                onChange={(checked) => void change(checked)}
              />
            </div>
            {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
          </div>
        )}
      </RemoteView>
    </Panel>
  );
}

export function DigestPreferencePanel() {
  const { user } = useSession();
  return canUse(user?.role, "queue") ? <DigestToggle /> : null;
}

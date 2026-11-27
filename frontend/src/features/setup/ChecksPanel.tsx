"use client";

import { useState } from "react";
import { CheckToggles } from "@/components/shared/practice-checks/CheckToggles";
import { sameChecks, withAllChecks } from "@/components/shared/practice-checks/checkList";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { useAction } from "@/hooks/useAction";
import { saveChecks } from "@/lib/api/practice";
import type { Checks } from "@/lib/api/types";
import { SETUP_TEXT } from "./strings";

interface ChecksPanelProps {
  checks: Checks;
  onSaved: () => void;
}

export function ChecksPanel({ checks, onSaved }: ChecksPanelProps) {
  const [draft, setDraft] = useState<Checks>(() => withAllChecks(checks));
  const [saved, setSaved] = useState(false);
  const save = useAction(saveChecks);
  const dirty = !sameChecks(draft, withAllChecks(checks));
  const words = SETUP_TEXT.checks;

  async function submit(): Promise<void> {
    const outcome = await save.run(draft);
    if (!outcome.ok) return;
    setSaved(true);
    onSaved();
  }

  return (
    <Panel aria-label={words.title}>
      <PanelHeader title={words.title} />
      <CheckToggles
        checks={draft}
        onChange={(key, on) => {
          setSaved(false);
          setDraft((current) => ({ ...current, [key]: on }));
        }}
      />
      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-hairline px-4 py-3">
        {save.error ? <InlineAlert tone="bad">{save.error}</InlineAlert> : null}
        {saved && !dirty ? (
          <span role="status" className="text-subhead text-secondary">
            {words.saved}
          </span>
        ) : null}
        <Button pending={save.pending} disabled={!dirty} onClick={() => void submit()}>
          {words.save}
        </Button>
      </div>
    </Panel>
  );
}

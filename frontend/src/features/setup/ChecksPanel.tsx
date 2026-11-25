"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { saveChecks } from "@/lib/api/practice";
import type { CheckKey, Checks } from "@/lib/api/types";
import { SETUP_TEXT } from "./strings";

const CHECK_ORDER: readonly CheckKey[] = ["em", "icd", "cdi", "audit", "mips"];

interface ChecksPanelProps {
  checks: Checks;
  onSaved: () => void;
}

export function ChecksPanel({ checks, onSaved }: ChecksPanelProps) {
  const [draft, setDraft] = useState<Checks>(checks);
  const [saved, setSaved] = useState(false);
  const save = useAction(saveChecks);
  const dirty = CHECK_ORDER.some((key) => draft[key] !== checks[key]);
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
      {CHECK_ORDER.map((key) => (
        <div key={key} className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
          <span>{words.labels[key]}</span>
          <Toggle
            label={words.labels[key]}
            checked={draft[key]}
            onChange={(on) => {
              setSaved(false);
              setDraft((current) => ({ ...current, [key]: on }));
            }}
          />
        </div>
      ))}
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

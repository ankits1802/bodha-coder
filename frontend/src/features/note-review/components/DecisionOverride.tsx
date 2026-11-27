"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import type { Finding, OverrideChoice } from "@/lib/api/types";
import { EMPTY_OVERRIDE, toOverride } from "../overrideReasons";
import { REVIEW_TEXT } from "../strings";
import { OverrideReasonPicker } from "./OverrideReasonPicker";

const WORDS = REVIEW_TEXT.override;

interface DecisionOverrideProps {
  subject: string;
  onConfirm: (override: OverrideChoice) => void;
  onCancel: () => void;
}

export function DecisionOverride({ subject, onConfirm, onCancel }: DecisionOverrideProps) {
  const [draft, setDraft] = useState(EMPTY_OVERRIDE);
  const [tried, setTried] = useState(false);

  function confirm(): void {
    setTried(true);
    const override = toOverride(draft);
    if (override) onConfirm(override);
  }

  return (
    <div className="rounded-field bg-muted-panel p-3.5">
      <OverrideReasonPicker
        label={WORDS.label(subject)}
        value={draft}
        showProblem={tried}
        autoFocus
        onChange={setDraft}
        onConfirm={confirm}
        onCancel={onCancel}
      >
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={confirm}>
            {WORDS.save}
          </Button>
          <Button size="sm" variant="plain" onClick={onCancel}>
            {WORDS.cancel}
          </Button>
        </div>
      </OverrideReasonPicker>
    </div>
  );
}

interface OverrideStatusProps {
  finding: Finding;
  editable: boolean;
  onAdd: () => void;
}

export function OverrideStatus({ finding, editable, onAdd }: OverrideStatusProps) {
  if (finding.override) {
    const label = WORDS.reasons[finding.override.reason];
    const said = finding.override.note ? `${label} · ${finding.override.note}` : label;
    return <span className="text-footnote text-secondary">{WORDS.given(said)}</span>;
  }
  if (!finding.override_needed) return null;
  return (
    <span className="flex flex-wrap items-center gap-3">
      <StatusDot tone="warn">{WORDS.needed}</StatusDot>
      {editable ? <TextButton onClick={onAdd}>{WORDS.add}</TextButton> : null}
    </span>
  );
}

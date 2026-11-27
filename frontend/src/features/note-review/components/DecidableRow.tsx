import type { ReactNode } from "react";
import type { Choice, Finding } from "@/lib/api/types";
import type { QuoteCheck } from "../findings";
import type { OverridePrompt } from "../useOverridePrompt";
import { DecisionControl } from "./DecisionControl";
import { DecisionOverride, OverrideStatus } from "./DecisionOverride";
import { FindingRow } from "./FindingRow";
import { FindingThread } from "./FindingThread";

export interface DecisionProps {
  editable: boolean;
  savingKey: string | null;
  currentKey: string | null;
  onChoose: (finding: Finding, choice: Choice) => void;
  onPicked: (finding: Finding, choice: Choice) => void;
  prompt?: OverridePrompt;
}

interface DecidableRowProps {
  finding: Finding;
  decision: DecisionProps;
  quote?: QuoteCheck | null;
  children?: ReactNode;
}

export function DecidableRow({ finding, decision, quote = null, children }: DecidableRowProps) {
  const { editable, savingKey, currentKey, onChoose, onPicked, prompt } = decision;
  const pending = prompt?.pending?.finding.key === finding.key ? prompt.pending : null;
  const shown = pending ? { ...finding, choice: pending.choice, decide_again: false } : finding;
  return (
    <FindingRow
      finding={finding}
      quote={quote}
      current={editable && currentKey === finding.key}
      decision={
        <DecisionControl finding={shown} editable={editable} busy={savingKey === finding.key} onChoose={onChoose} onPicked={onPicked} />
      }
    >
      {pending && prompt ? (
        <DecisionOverride subject={finding.title} onConfirm={prompt.confirm} onCancel={prompt.cancel} />
      ) : (
        <OverrideStatus finding={finding} editable={editable && Boolean(prompt)} onAdd={() => prompt?.addReason(finding)} />
      )}
      <FindingThread findingKey={finding.key} title={finding.title} />
      {children}
    </FindingRow>
  );
}

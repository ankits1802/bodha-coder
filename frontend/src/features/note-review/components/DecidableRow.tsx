import type { ReactNode } from "react";
import type { Choice, Finding } from "@/lib/api/types";
import type { QuoteCheck } from "../findings";
import { DecisionControl } from "./DecisionControl";
import { FindingRow } from "./FindingRow";

export interface DecisionProps {
  editable: boolean;
  savingKey: string | null;
  currentKey: string | null;
  onChoose: (finding: Finding, choice: Choice) => void;
  onPicked: (finding: Finding) => void;
}

interface DecidableRowProps {
  finding: Finding;
  decision: DecisionProps;
  quote?: QuoteCheck | null;
  children?: ReactNode;
}

export function DecidableRow({ finding, decision, quote = null, children }: DecidableRowProps) {
  const { editable, savingKey, currentKey, onChoose, onPicked } = decision;
  return (
    <FindingRow
      finding={finding}
      quote={quote}
      current={editable && currentKey === finding.key}
      decision={
        <DecisionControl finding={finding} editable={editable} busy={savingKey === finding.key} onChoose={onChoose} onPicked={onPicked} />
      }
    >
      {children}
    </FindingRow>
  );
}

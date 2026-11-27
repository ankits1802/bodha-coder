"use client";

import { useRef } from "react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { Choice, Finding } from "@/lib/api/types";
import { shownChoice } from "../decisionFlow";
import { choiceLabel } from "../findings";
import { REVIEW_TEXT } from "../strings";

interface DecisionControlProps {
  finding: Finding;
  editable: boolean;
  busy: boolean;
  onChoose: (finding: Finding, choice: Choice) => void;
  onPicked?: (finding: Finding, choice: Choice) => void;
}

export function DecisionControl({ finding, editable, busy, onChoose, onPicked }: DecisionControlProps) {
  const clicked = useRef(false);
  const value = shownChoice(finding);
  if (finding.allowed.length < 2) return null;
  if (!editable) return <span className="text-subhead text-secondary">{choiceLabel(finding, finding.choice)}</span>;
  return (
    <div
      aria-busy={busy || undefined}
      onClickCapture={() => {
        clicked.current = true;
      }}
      onClick={() => {
        clicked.current = false;
      }}
    >
      <SegmentedControl
        label={REVIEW_TEXT.decisionLabel(finding.title)}
        value={value}
        orientation="horizontal"
        segments={finding.allowed.map((choice) => ({ value: choice, label: choiceLabel(finding, choice) }))}
        onChange={(choice) => {
          const byClick = clicked.current;
          clicked.current = false;
          if (choice !== value) onChoose(finding, choice);
          if (byClick) onPicked?.(finding, choice);
        }}
      />
    </div>
  );
}

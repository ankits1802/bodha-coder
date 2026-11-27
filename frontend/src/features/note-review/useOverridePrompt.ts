"use client";

import { useState } from "react";
import type { Choice, Finding, OverrideChoice } from "@/lib/api/types";
import { departsWith } from "./overrideReasons";
import type { Decisions } from "./useDecisions";

export interface PendingOverride {
  finding: Finding;
  choice: Choice;
}

export interface OverridePrompt {
  pending: PendingOverride | null;
  request: (finding: Finding, choice: Choice) => void;
  addReason: (finding: Finding) => void;
  confirm: (override: OverrideChoice) => void;
  cancel: () => void;
}

export function useOverridePrompt(decisions: Decisions): OverridePrompt {
  const [pending, setPending] = useState<PendingOverride | null>(null);

  function request(finding: Finding, choice: Choice): void {
    if (departsWith(finding, choice)) {
      setPending({ finding, choice });
      return;
    }
    setPending(null);
    decisions.choose(finding, choice);
  }

  function confirm(override: OverrideChoice): void {
    if (!pending) return;
    decisions.choose(pending.finding, pending.choice, override);
    setPending(null);
  }

  return {
    pending,
    request,
    addReason: (finding) => setPending({ finding, choice: finding.choice }),
    confirm,
    cancel: () => setPending(null),
  };
}

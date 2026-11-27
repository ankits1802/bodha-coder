"use client";

import { useShortcuts } from "@/components/shared/shortcuts/useShortcuts";
import type { Finding, NoteDetail } from "@/lib/api/types";
import { choiceFor } from "./decisionFlow";
import { departsWith } from "./overrideReasons";
import type { ReviewPermissions } from "./permissions";
import type { Decisions } from "./useDecisions";
import type { FindingFocus } from "./useFindingFocus";
import type { OverridePrompt } from "./useOverridePrompt";

export interface FindingKeys {
  detail: NoteDetail;
  permissions: ReviewPermissions;
  focus: FindingFocus;
  prompt: OverridePrompt;
  decisions: Decisions;
  toAccept: Finding[];
  onEditCodes: () => void;
}

export function useFindingKeys({ detail, permissions, focus, prompt, decisions, toAccept, onEditCodes }: FindingKeys): void {
  const idle = permissions.decide && prompt.pending === null;
  const deciding = idle && focus.currentKey !== null;

  function decideCurrent(accept: boolean): void {
    const finding = detail.findings.find((item) => item.key === focus.currentKey);
    const choice = finding ? choiceFor(finding, accept) : null;
    if (!finding || !choice) return;
    prompt.request(finding, choice);
    if (!departsWith(finding, choice)) focus.moveAfter(finding.key);
  }

  useShortcuts("review", {
    acceptFinding: deciding ? () => decideCurrent(true) : undefined,
    rejectFinding: deciding ? () => decideCurrent(false) : undefined,
    nextFinding: idle ? () => focus.step(1) : undefined,
    previousFinding: idle ? () => focus.step(-1) : undefined,
    acceptSupported: idle && toAccept.length > 0 ? () => decisions.acceptAll(toAccept) : undefined,
    editBilled: idle ? onEditCodes : undefined,
  });
}

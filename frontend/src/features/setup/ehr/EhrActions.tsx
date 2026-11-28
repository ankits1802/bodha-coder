"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAction } from "@/hooks/useAction";
import { pauseEhrPulls, resumeEhrPulls, testEhrConnection } from "@/lib/api/ehrConnection";
import type { EhrCheck, EhrConnection } from "@/lib/api/types";
import { EHR_TEXT } from "./strings";

interface EhrActionsProps {
  view: EhrConnection;
  onChange: (view: EhrConnection) => void;
}

const words = EHR_TEXT;

function CheckSteps({ check }: { check: EhrCheck }) {
  return (
    <ul aria-label={words.test} className="m-0 flex list-none flex-col gap-1.5 p-0">
      {check.steps.map((step) => (
        <li key={step.step} className="flex flex-col gap-0.5">
          <StatusDot tone={step.passed ? "ok" : "bad"}>{words.steps[step.step]}</StatusDot>
          <span className="text-footnote break-all text-secondary">{step.detail}</span>
        </li>
      ))}
    </ul>
  );
}

export function EhrActions({ view, onChange }: EhrActionsProps) {
  const test = useAction(testEhrConnection);
  const pause = useAction(pauseEhrPulls);
  const resume = useAction(resumeEhrPulls);
  const toggle = view.connection?.paused ? resume : pause;
  const [check, setCheck] = useState<EhrCheck | null>(null);

  async function runTest(): Promise<void> {
    setCheck(null);
    const outcome = await test.run();
    if (outcome.ok) setCheck(outcome.value);
  }

  async function flip(): Promise<void> {
    const outcome = await toggle.run();
    if (outcome.ok) onChange(outcome.value);
  }

  if (!view.connection) return null;
  return (
    <div className="flex flex-col gap-3 border-t border-hairline px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" pending={test.pending} disabled={!view.registration} onClick={() => void runTest()}>
          {words.test}
        </Button>
        <Button size="sm" pending={toggle.pending} onClick={() => void flip()}>
          {view.connection.paused ? words.resume : words.pause}
        </Button>
      </div>
      {check ? <CheckSteps check={check} /> : null}
      {test.error ? <InlineAlert tone="bad">{test.error}</InlineAlert> : null}
      {toggle.error ? <InlineAlert tone="bad">{toggle.error}</InlineAlert> : null}
    </div>
  );
}

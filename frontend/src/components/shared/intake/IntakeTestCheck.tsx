"use client";

import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Spinner } from "@/components/ui/Spinner";
import { StatusDot } from "@/components/ui/StatusDot";
import { formatTime } from "@/lib/format";
import { EMAIL_INTAKE_TEXT } from "./strings";
import { useIntakeTest, type IntakeTestCheck as Check } from "./useIntakeTest";

const words = EMAIL_INTAKE_TEXT;

function TestStatus({ check }: { check: Check }) {
  if (check.waiting) return <Spinner size="sm" label={words.waiting} />;
  if (check.test?.arrived_at) {
    return (
      <span role="status">
        <StatusDot tone="ok">{words.arrived(formatTime(check.test.arrived_at))}</StatusDot>
      </span>
    );
  }
  if (check.timedOut) {
    return (
      <span role="status">
        <StatusDot tone="warn">{words.notArrived}</StatusDot>
      </span>
    );
  }
  return null;
}

export function IntakeTestCheck({ onArrived }: { onArrived: () => void }) {
  const check = useIntakeTest(onArrived);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline px-4 py-3">
      <span className="text-subhead font-medium text-label">{words.test}</span>
      <div className="flex flex-wrap items-center justify-end gap-3">
        <TestStatus check={check} />
        {check.error ? <InlineAlert tone="bad">{check.error}</InlineAlert> : null}
        <Button size="sm" pending={check.pending} disabled={check.waiting} onClick={() => void check.send()}>
          {words.sendTest}
        </Button>
      </div>
    </div>
  );
}

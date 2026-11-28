"use client";

import { useEffect, useState } from "react";
import { useAction } from "@/hooks/useAction";
import { getIntakeTest, sendIntakeTest } from "@/lib/api/emailIntake";
import type { IntakeTest } from "@/lib/api/types";

export const TEST_POLL_MS = 5000;
export const TEST_POLLS = 60;

export interface IntakeTestCheck {
  test: IntakeTest | null;
  waiting: boolean;
  timedOut: boolean;
  pending: boolean;
  error: string | null;
  send: () => Promise<void>;
}

export function useIntakeTest(onArrived: () => void): IntakeTestCheck {
  const [test, setTest] = useState<IntakeTest | null>(null);
  const [polls, setPolls] = useState(0);
  const sender = useAction(sendIntakeTest);
  const unanswered = test !== null && test.arrived_at === null;
  const waiting = unanswered && polls < TEST_POLLS;

  useEffect(() => {
    if (!waiting || test === null) return;
    const timer = window.setTimeout(() => {
      getIntakeTest(test.id).then(
        (next) => {
          setTest(next);
          setPolls((count) => count + 1);
          if (next.arrived_at) onArrived();
        },
        () => setPolls((count) => count + 1),
      );
    }, TEST_POLL_MS);
    return () => window.clearTimeout(timer);
  }, [waiting, test, polls, onArrived]);

  async function send(): Promise<void> {
    const outcome = await sender.run();
    if (!outcome.ok) return;
    setPolls(0);
    setTest(outcome.value);
  }

  return { test, waiting, timedOut: unanswered && !waiting, pending: sender.pending, error: sender.error, send };
}

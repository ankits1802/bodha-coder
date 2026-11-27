"use client";

import { useEffect, useRef, useState } from "react";
import { messageOf } from "@/lib/api/errors";
import { saveDecisions } from "@/lib/api/notes";
import type { Choice, Finding, NoteDetail } from "@/lib/api/types";
import { withChoice } from "./decisionFlow";

export interface Decisions {
  choose: (finding: Finding, choice: Choice) => void;
  idle: () => Promise<void>;
  savingKey: string | null;
  error: string | null;
}

export function useDecisions(detail: NoteDetail, onReplace: (detail: NoteDetail) => void): Decisions {
  const shown = useRef(detail);
  const confirmed = useRef(detail);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const ticket = useRef(0);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    shown.current = detail;
  }, [detail]);

  function settle(mine: number, next: NoteDetail): void {
    confirmed.current = next;
    if (mine !== ticket.current) return;
    setSavingKey(null);
    onReplace(next);
  }

  function choose(finding: Finding, choice: Choice): void {
    if (finding.choice === choice) return;
    const optimistic = withChoice(shown.current, finding.key, choice);
    shown.current = optimistic;
    ticket.current += 1;
    const mine = ticket.current;
    setError(null);
    setSavingKey(finding.key);
    onReplace(optimistic);
    queue.current = queue.current.then(() =>
      saveDecisions(detail.note.id, { [finding.key]: choice }).then(
        (saved) => settle(mine, saved),
        (caught: unknown) => {
          setError(messageOf(caught));
          settle(mine, confirmed.current);
        },
      ),
    );
  }

  return { choose, idle: () => queue.current, savingKey, error };
}

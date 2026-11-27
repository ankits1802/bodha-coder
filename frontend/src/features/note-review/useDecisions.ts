"use client";

import { useEffect, useRef, useState } from "react";
import { messageOf } from "@/lib/api/errors";
import { saveDecisions } from "@/lib/api/notes";
import type { Choice, Finding, NoteDetail, OverrideChoice } from "@/lib/api/types";
import { withChoices } from "./decisionFlow";

export interface Decisions {
  choose: (finding: Finding, choice: Choice, override?: OverrideChoice) => void;
  acceptAll: (findings: Finding[]) => void;
  idle: () => Promise<void>;
  savingKey: string | null;
  error: string | null;
}

export const ALL_KEYS = "*";

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

  function save(savingFor: string, choices: Record<string, Choice>, reasons: Record<string, OverrideChoice>): void {
    const optimistic = withChoices(shown.current, choices);
    shown.current = optimistic;
    ticket.current += 1;
    const mine = ticket.current;
    setError(null);
    setSavingKey(savingFor);
    onReplace(optimistic);
    queue.current = queue.current.then(() =>
      saveDecisions(detail.note.id, choices, reasons).then(
        (saved) => settle(mine, saved),
        (caught: unknown) => {
          setError(messageOf(caught));
          settle(mine, confirmed.current);
        },
      ),
    );
  }

  function choose(finding: Finding, choice: Choice, override?: OverrideChoice): void {
    if (finding.choice === choice && !override && !finding.decide_again) return;
    save(finding.key, { [finding.key]: choice }, override ? { [finding.key]: override } : {});
  }

  function acceptAll(findings: Finding[]): void {
    const choices = Object.fromEntries(findings.flatMap((finding) => (finding.allowed[0] ? [[finding.key, finding.allowed[0]]] : [])));
    if (Object.keys(choices).length > 0) save(ALL_KEYS, choices, {});
  }

  return { choose, acceptAll, idle: () => queue.current, savingKey, error };
}

"use client";

import { useId } from "react";
import { KeyHint } from "@/components/shared/shortcuts/KeyHint";
import { Button } from "@/components/ui/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import { TextButton } from "@/components/ui/TextButton";
import type { Finding, NoteText } from "@/lib/api/types";
import { quoteCheck } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { FindingRow } from "./FindingRow";

const WORDS = REVIEW_TEXT.supported;

interface SupportedGroupProps {
  findings: Finding[];
  texts: NoteText[];
  open: boolean;
  onToggle: () => void;
  onAcceptAll: (() => void) | null;
  pending: boolean;
}

export function SupportedGroup({ findings, texts, open, onToggle, onAcceptAll, pending }: SupportedGroupProps) {
  const listId = useId();
  if (findings.length === 0) return null;
  const accepted = findings.every((finding) => finding.decided);
  return (
    <section aria-label={WORDS.toggle(findings.length)} className="border-t border-hairline">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
        <TextButton aria-expanded={open} aria-controls={listId} onClick={onToggle}>
          {WORDS.toggle(findings.length)}
        </TextButton>
        {onAcceptAll ? (
          <Button size="sm" onClick={onAcceptAll} pending={pending}>
            {WORDS.accept} <KeyHint shortcut="acceptSupported" />
          </Button>
        ) : accepted ? (
          <StatusDot tone="ok">{WORDS.accepted}</StatusDot>
        ) : null}
      </div>
      {open ? (
        <ul id={listId} className="m-0 list-none border-t border-hairline p-0">
          {findings.map((finding) => (
            <FindingRow key={finding.key} finding={finding} quote={quoteCheck(finding, texts)} />
          ))}
        </ul>
      ) : null}
    </section>
  );
}

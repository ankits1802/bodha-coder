import { CodeList } from "@/components/shared/CodeList";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { AnalysisStatus, DecisionRecord, NoteDetail, OverrideReason } from "@/lib/api/types";
import { codeLabel } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { HistoryEntry, HistoryList, joinMeta } from "./HistoryEntry";

const ANALYSIS_TONES: Record<AnalysisStatus, StatusTone> = {
  queued: "warn",
  running: "warn",
  succeeded: "ok",
  failed: "bad",
  superseded: "neutral",
};

const words = REVIEW_TEXT.history;

function reasonLabel(reason: string): string {
  return words.reason[reason] ?? reason;
}

export function byLabel(name: string | null, role: string | null = null): string {
  return words.by(role && name ? `${name} (${role})` : (name ?? words.system));
}

function overrideLabel(reason: OverrideReason | null, note: string | null): string | null {
  if (!reason) return null;
  const label = REVIEW_TEXT.override.reasons[reason];
  return REVIEW_TEXT.override.given(note ? `${label} · ${note}` : label);
}

export function Readings({ detail }: { detail: NoteDetail }) {
  return (
    <HistoryList>
      {detail.history.analyses.map((analysis) => (
        <HistoryEntry
          key={analysis.revision}
          at={analysis.finished_at}
          title={
            <>
              <span className="font-medium">{words.revision(analysis.revision)}</span>
              <StatusDot tone={ANALYSIS_TONES[analysis.status]}>{words.analysisStatus[analysis.status]}</StatusDot>
            </>
          }
          meta={joinMeta([reasonLabel(analysis.reason), analysis.model, analysis.error])}
        />
      ))}
    </HistoryList>
  );
}

export function CodeRevisions({ detail }: { detail: NoteDetail }) {
  return (
    <HistoryList>
      {detail.history.code_sets.map((set) => (
        <HistoryEntry
          key={`${set.kind}-${set.revision}`}
          at={set.at}
          title={
            <>
              <span className="font-medium">{set.kind === "billed" ? words.billedKind : words.finalKind}</span>
              <span className="text-footnote text-secondary">{words.revision(set.revision)}</span>
            </>
          }
          meta={joinMeta([reasonLabel(set.reason), byLabel(set.by, set.role), overrideLabel(set.override_reason, set.override_note)])}
        >
          <CodeList codes={set.codes.map(codeLabel)} />
        </HistoryEntry>
      ))}
    </HistoryList>
  );
}

function decisionTitle(decision: DecisionRecord, titles: Map<string, string>): string {
  const linked = decision.pointers;
  if (!linked) return titles.get(decision.key) || decision.key;
  return linked.diagnoses.length > 0 ? words.linked(linked.code, linked.diagnoses.join(", ")) : words.linkedDefault(linked.code);
}

export function Decisions({ detail }: { detail: NoteDetail }) {
  const titles = new Map(detail.findings.map((finding) => [finding.key, finding.title]));
  return (
    <HistoryList>
      {detail.history.decisions.map((decision, index) => (
        <HistoryEntry
          key={`${decision.key}-${decision.at}-${index}`}
          at={decision.at}
          title={<span className="font-medium">{decisionTitle(decision, titles)}</span>}
          meta={joinMeta([
            decision.pointers ? null : words.chose(REVIEW_TEXT.choices[decision.choice]),
            byLabel(decision.by, decision.role),
            overrideLabel(decision.override_reason, decision.override_note),
          ])}
        />
      ))}
    </HistoryList>
  );
}

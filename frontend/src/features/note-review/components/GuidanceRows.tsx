import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { Finding } from "@/lib/api/types";
import { textValue } from "../findings";
import { REVIEW_TEXT } from "../strings";

const SEVERITY_TONES: Record<string, StatusTone> = { Critical: "bad", High: "bad", Medium: "warn", Low: "neutral" };
const ROW = "flex flex-col gap-1.5 border-t border-hairline px-5 py-4 first:border-t-0";

export function WordingBlock({ gap }: { gap: Finding }) {
  const words = REVIEW_TEXT.wording;
  const recommendation = textValue(gap.detail.recommendation);
  const suggested = textValue(gap.detail.suggested_text);
  const current = gap.evidence[0];
  return (
    <div className="flex flex-col gap-1.5">
      {current ? (
        <span className="text-callout text-secondary">
          {words.current} <q>{current}</q>
        </span>
      ) : null}
      {recommendation ? <span className="text-callout">{recommendation}</span> : null}
      {suggested ? (
        <figure className="m-0 rounded-field bg-muted-panel px-3.5 py-2.5">
          <figcaption className="text-caption text-secondary">{words.suggested}</figcaption>
          <p className="m-0 whitespace-pre-wrap">{suggested}</p>
        </figure>
      ) : null}
    </div>
  );
}

function marker(finding: Finding): { tone: StatusTone; label: string } | null {
  if (!finding.severity) return null;
  if (finding.kind === "cdi_gap") return { tone: "neutral", label: REVIEW_TEXT.wording.priority(finding.severity) };
  return { tone: SEVERITY_TONES[finding.severity] ?? "neutral", label: REVIEW_TEXT.audit.severity(finding.severity) };
}

export function GuidanceRow({ finding }: { finding: Finding }) {
  const shown = marker(finding);
  const gap = finding.kind === "cdi_gap";
  return (
    <li data-finding-key={finding.key} className={ROW}>
      <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="font-medium">{finding.title}</span>
        {shown ? <StatusDot tone={shown.tone}>{shown.label}</StatusDot> : null}
      </span>
      {!gap && finding.reasoning ? <span className="text-callout text-secondary">{finding.reasoning}</span> : null}
      {gap ? <WordingBlock gap={finding} /> : null}
    </li>
  );
}

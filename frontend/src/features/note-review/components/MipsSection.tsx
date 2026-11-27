import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { Finding } from "@/lib/api/types";
import { measureStatus, type MeasureStatus } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { ReviewSection } from "./ReviewSection";

const STATUS_TONES: Record<MeasureStatus, StatusTone> = { met: "ok", missing: "warn", not_applicable: "neutral" };

function MeasureRow({ measure }: { measure: Finding }) {
  const status = measureStatus(measure);
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
      <span className="min-w-0 flex-[1_1_14rem]">
        <span className="font-medium">{measure.title}</span>
        {measure.reasoning ? <span className="block text-callout text-secondary">{measure.reasoning}</span> : null}
      </span>
      {status ? <StatusDot tone={STATUS_TONES[status]}>{REVIEW_TEXT.audit.measureStatus[status]}</StatusDot> : null}
    </li>
  );
}

export function MipsSection({ measures }: { measures: Finding[] }) {
  if (measures.length === 0) return null;
  return (
    <ReviewSection title={REVIEW_TEXT.audit.mips}>
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {measures.map((measure) => (
          <MeasureRow key={measure.key} measure={measure} />
        ))}
      </ul>
    </ReviewSection>
  );
}

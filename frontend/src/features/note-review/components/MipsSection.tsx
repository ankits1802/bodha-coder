import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import type { Finding } from "@/lib/api/types";
import { measureStatus, type MeasureStatus } from "../findings";
import { practiceMark, practiceReportCodes } from "../practiceMeasures";
import { REVIEW_TEXT } from "../strings";
import { ReviewSection } from "./ReviewSection";

const STATUS_TONES: Record<MeasureStatus, StatusTone> = { met: "ok", missing: "warn", not_applicable: "neutral" };
const words = REVIEW_TEXT.audit;

function MeasureRow({ measure }: { measure: Finding }) {
  const status = measureStatus(measure);
  const practice = practiceMark(measure);
  const report = practice ? practiceReportCodes(measure, status) : [];
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
      <span className="min-w-0 flex-[1_1_14rem]">
        <span className="font-medium">{measure.title}</span>
        {practice ? <span className="block text-caption font-semibold text-tertiary">{words.practiceMeasure(practice.identifier)}</span> : null}
        {measure.reasoning ? <span className="block text-callout text-secondary">{measure.reasoning}</span> : null}
        {report.length > 0 ? <span className="block text-callout text-secondary">{words.reportCodes(report.join(", "))}</span> : null}
      </span>
      {status ? <StatusDot tone={STATUS_TONES[status]}>{words.measureStatus[status]}</StatusDot> : null}
    </li>
  );
}

export function MipsSection({ measures }: { measures: Finding[] }) {
  if (measures.length === 0) return null;
  return (
    <ReviewSection title={words.mips}>
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {measures.map((measure) => (
          <MeasureRow key={measure.key} measure={measure} />
        ))}
      </ul>
    </ReviewSection>
  );
}

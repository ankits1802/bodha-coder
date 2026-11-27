import { CodeList } from "@/components/shared/CodeList";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { formatRiskScore, type RiskCategory, type RiskStatus, type RiskSummary } from "../findings";
import { REVIEW_TEXT } from "../strings";
import { ReviewSection } from "./ReviewSection";

const STATUS_TONES: Record<RiskStatus, StatusTone> = { captured: "ok", missed: "warn", unsupported: "bad" };

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="-ml-px flex flex-col gap-0.5 border-l border-hairline px-5.5 first:border-l-0 first:pl-0">
      <dt className="text-caption text-secondary">{label}</dt>
      <dd className="m-0 text-headline font-semibold tracking-headline tabular-nums">{formatRiskScore(value)}</dd>
    </div>
  );
}

export function RiskScores({ summary }: { summary: RiskSummary }) {
  const words = REVIEW_TEXT.risk;
  const model = summary.model && summary.paymentYear ? words.model(summary.model, summary.paymentYear) : null;
  const facts = [model, summary.segment, summary.ageFromNote ? words.ageFromNote : null].filter(Boolean);
  return (
    <ReviewSection title={words.scores}>
      <dl className="m-0 flex flex-wrap gap-y-3">
        <Score label={words.scoreBilled} value={summary.scoreBilled} />
        <Score label={words.scoreDocumented} value={summary.scoreDocumented} />
      </dl>
      {facts.length > 0 ? <p className="m-0 text-footnote text-secondary">{facts.join(" · ")}</p> : null}
    </ReviewSection>
  );
}

function CategoryRow({ category }: { category: RiskCategory }) {
  const words = REVIEW_TEXT.risk;
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
      <span className="flex min-w-0 flex-[1_1_16rem] flex-col gap-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium tabular-nums">{category.hcc}</span>
          <span>{category.label}</span>
        </span>
        <span className="flex flex-wrap items-center gap-2 text-callout text-secondary">
          <CodeList codes={category.codes} />
          {category.factor !== null ? <span className="tabular-nums">{words.factor(formatRiskScore(category.factor))}</span> : null}
        </span>
      </span>
      <StatusDot tone={STATUS_TONES[category.status]}>{words.status[category.status]}</StatusDot>
    </li>
  );
}

export function RiskCategories({ categories }: { categories: RiskCategory[] }) {
  const words = REVIEW_TEXT.risk;
  return (
    <ReviewSection title={words.categories}>
      {categories.length === 0 ? <p className="m-0 text-secondary">{words.noCategories}</p> : null}
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {categories.map((category) => (
          <CategoryRow key={category.hcc} category={category} />
        ))}
      </ul>
    </ReviewSection>
  );
}

import type { ReactNode } from "react";
import type { BillingInterval, PlanTerms } from "@/lib/api/types";
import { PLAN_LABELS } from "@/lib/labels";
import { cardPrice, limitLines } from "./planPrice";

interface PlanCardProps {
  terms: PlanTerms;
  interval: BillingInterval;
  trialDays: number;
  title?: ReactNode;
  detailsId?: string;
  className?: string;
  children?: ReactNode;
}

export function PlanCard({ terms, interval, trialDays, title, detailsId, className = "", children }: PlanCardProps) {
  const price = cardPrice(terms, interval, trialDays);
  return (
    <article className={`relative flex min-w-0 flex-col gap-4 rounded-panel bg-surface p-5 shadow-panel ${className}`}>
      <h3 className="m-0 text-headline font-semibold tracking-headline">{title ?? PLAN_LABELS[terms.key]}</h3>
      <div id={detailsId} className="flex flex-col gap-4">
        <p className="m-0 flex flex-wrap items-baseline gap-x-1.5">
          <span className="text-stat font-bold tracking-title tabular-nums">{price.amount}</span>
          <span className="text-footnote text-secondary">{price.unit}</span>
        </p>
        <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-body text-label-soft">
          {limitLines(terms).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
      {children ? <div className="mt-auto flex flex-col gap-2 pt-1">{children}</div> : null}
    </article>
  );
}

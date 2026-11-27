import type { ReactNode } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusDot } from "@/components/ui/StatusDot";
import type { HqPractice } from "@/lib/api/types";
import { FORMAT_WORDS, formatCalendarDay, formatCount } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { renewalLine } from "../practiceStatus";
import { billingView } from "../practices/practiceBilling";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.practice.plan;

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-hairline px-4.5 py-3.5 last:border-b-0 sm:flex-row sm:gap-6">
      <dt className="text-subhead text-secondary sm:w-44 sm:flex-none">{label}</dt>
      <dd className="m-0 min-w-0">{children}</dd>
    </div>
  );
}

function Billing({ practice }: { practice: HqPractice }) {
  const view = billingView(practice);
  if (!view) return <span className="text-secondary">{words.noBilling}</span>;
  return <StatusDot tone={view.tone}>{view.label}</StatusDot>;
}

function Started({ practice }: { practice: HqPractice }) {
  const day = formatCalendarDay(practice.signed_up_on, "year");
  return <>{practice.source ? words.startedOn(words.startedBy[practice.source], day) : day}</>;
}

export function PlanTab({ practice }: { practice: HqPractice }) {
  return (
    <Panel aria-label={words.label}>
      <dl className="m-0">
        <Fact label={words.plan}>{PLAN_LABELS[practice.plan]}</Fact>
        <Fact label={words.renewal}>{renewalLine(practice)}</Fact>
        <Fact label={words.billing}>
          <Billing practice={practice} />
        </Fact>
        <Fact label={words.users}>
          <span className="tabular-nums">{words.usersOfSeats(formatCount(practice.users), formatCount(practice.seats))}</span>
        </Fact>
        <Fact label={words.providers}>
          <span className="tabular-nums">{formatCount(practice.providers)}</span>
        </Fact>
        <Fact label={words.admin}>
          {practice.admin_name ? (
            <span className="flex flex-col">
              <span>{practice.admin_name}</span>
              <span className="text-footnote text-secondary">{practice.admin_email ?? FORMAT_WORDS.empty}</span>
            </span>
          ) : (
            <span className="text-tertiary">{HQ_TEXT.practices.noAdmin}</span>
          )}
        </Fact>
        <Fact label={words.timeZone}>{practice.time_zone}</Fact>
        <Fact label={words.started}>
          <Started practice={practice} />
        </Fact>
      </dl>
    </Panel>
  );
}

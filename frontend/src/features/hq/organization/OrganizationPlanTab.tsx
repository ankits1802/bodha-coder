import type { ReactNode } from "react";
import { Panel } from "@/components/ui/Panel";
import { StatusDot, type StatusTone } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqOrganization, OrganizationPlan, PlanStanding } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { organizationRenewal } from "../organizationStatus";
import { billingView } from "../practices/practiceBilling";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.organization.plan;
const STANDING_TONES: Record<PlanStanding, StatusTone> = {
  trial: "low",
  active: "ok",
  past_due: "warn",
  canceling: "warn",
  canceled: "bad",
  ended: "bad",
  managed: "ok",
};

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-hairline px-4.5 py-3.5 last:border-b-0 sm:flex-row sm:gap-6">
      <dt className="text-subhead text-secondary sm:w-44 sm:flex-none">{label}</dt>
      <dd className="m-0 min-w-0">{children}</dd>
    </div>
  );
}

function limitOf(limit: number | null): string | null {
  return limit === null ? null : formatCount(limit);
}

function UsageTable({ plan }: { plan: OrganizationPlan }) {
  const columns = words.columns;
  return (
    <Table label={words.usageLabel} minWidth="md">
      <thead>
        <tr>
          <Th>{columns.practice}</Th>
          <Th className="text-right">{columns.providers}</Th>
          <Th className="text-right">{columns.users}</Th>
        </tr>
      </thead>
      <tbody>
        {plan.practices.map((practice) => (
          <Tr key={practice.id}>
            <Td>{practice.name}</Td>
            <Td className="text-right tabular-nums">{words.usage(formatCount(practice.providers), limitOf(practice.provider_limit))}</Td>
            <Td className="text-right tabular-nums">{words.usage(formatCount(practice.users), limitOf(practice.user_limit))}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

export function OrganizationPlanTab({ organization, plan }: { organization: HqOrganization; plan: OrganizationPlan }) {
  const billing = billingView(organization);
  return (
    <>
      <Panel aria-label={words.label}>
        <dl className="m-0">
          <Fact label={words.plan}>{PLAN_LABELS[plan.plan]}</Fact>
          <Fact label={words.standing}>
            <StatusDot tone={STANDING_TONES[plan.standing]}>{words.standings[plan.standing]}</StatusDot>
          </Fact>
          <Fact label={words.renewal}>{organizationRenewal(organization)}</Fact>
          <Fact label={words.billing}>
            {billing ? <StatusDot tone={billing.tone}>{billing.label}</StatusDot> : <span className="text-secondary">{words.noBilling}</span>}
          </Fact>
          <Fact label={words.providers}>
            <span className="tabular-nums">{formatCount(plan.providers)}</span>
          </Fact>
        </dl>
      </Panel>
      {plan.practices.length > 0 ? (
        <Panel aria-label={words.usageLabel}>
          <UsageTable plan={plan} />
        </Panel>
      ) : null}
    </>
  );
}

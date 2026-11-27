import Link from "next/link";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { HqOrganization } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import { PLAN_LABELS } from "@/lib/labels";
import { organizationHref } from "../organization/organizationTabs";
import { organizationRenewal, organizationStatusView } from "../organizationStatus";
import { billingView } from "../practices/practiceBilling";
import { HQ_TEXT } from "../strings";

const words = HQ_TEXT.organizations;

function OrganizationRow({ organization }: { organization: HqOrganization }) {
  const status = organizationStatusView(organization);
  const billing = billingView(organization);
  return (
    <Tr>
      <Td>
        <Link href={organizationHref(organization.id)} className="font-medium text-label hover:underline">
          {organization.name}
        </Link>
        <span className="block text-footnote text-secondary">{words.providers(organization.providers)}</span>
      </Td>
      <Td>{words.practices(organization.practices, organization.combined_practices)}</Td>
      <Td className="text-right tabular-nums">{formatCount(organization.admins)}</Td>
      <Td>
        {PLAN_LABELS[organization.plan]}
        <span className="block text-footnote text-secondary">{organizationRenewal(organization)}</span>
        {billing ? (
          <StatusDot tone={billing.tone} className="mt-0.5 text-footnote">
            {billing.label}
          </StatusDot>
        ) : null}
      </Td>
      <Td>
        <StatusDot tone={status.tone}>{status.label}</StatusDot>
      </Td>
    </Tr>
  );
}

export function OrganizationsTable({ organizations }: { organizations: HqOrganization[] }) {
  const columns = words.columns;
  return (
    <Table label={words.tableLabel} minWidth="lg">
      <thead>
        <tr>
          <Th>{columns.organization}</Th>
          <Th>{columns.practices}</Th>
          <Th className="text-right">{columns.admins}</Th>
          <Th>{columns.plan}</Th>
          <Th>{columns.status}</Th>
        </tr>
      </thead>
      <tbody>
        {organizations.map((organization) => (
          <OrganizationRow key={organization.id} organization={organization} />
        ))}
      </tbody>
    </Table>
  );
}

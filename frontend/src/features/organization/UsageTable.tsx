import { PLAN_CHOOSER_TEXT } from "@/components/shared/plan-chooser/strings";
import { EmptyState } from "@/components/ui/EmptyState";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { PracticeUsage } from "@/lib/api/types";
import { ORGANIZATION_TEXT } from "./strings";

const words = ORGANIZATION_TEXT.plan;
const NUMBER = "text-right tabular-nums";

export function UsageTable({ practices }: { practices: readonly PracticeUsage[] }) {
  if (practices.length === 0) return <EmptyState title={words.emptyUsage} />;
  return (
    <Table label={words.usageLabel} minWidth="sm">
      <thead>
        <tr>
          <Th>{words.columns.practice}</Th>
          <Th className="text-right">{words.columns.providers}</Th>
          <Th className="text-right">{words.columns.users}</Th>
        </tr>
      </thead>
      <tbody>
        {practices.map((practice) => (
          <Tr key={practice.id}>
            <Td className="text-body font-medium text-label">{practice.name}</Td>
            <Td className={NUMBER}>{PLAN_CHOOSER_TEXT.usage(practice.providers, practice.provider_limit)}</Td>
            <Td className={NUMBER}>{PLAN_CHOOSER_TEXT.usage(practice.users, practice.user_limit)}</Td>
          </Tr>
        ))}
      </tbody>
    </Table>
  );
}

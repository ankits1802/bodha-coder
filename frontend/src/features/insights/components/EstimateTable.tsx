import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { InsightEstimates } from "@/lib/api/types";
import { formatCount, formatMoneyChange } from "@/lib/format";
import { INSIGHTS_TEXT } from "../strings";

export function EstimateTable({ estimates }: { estimates: InsightEstimates }) {
  const words = INSIGHTS_TEXT.estimateColumns;
  return (
    <Panel>
      <PanelHeader title={INSIGHTS_TEXT.estimatesTitle} />
      {estimates.providers.length === 0 ? (
        <EmptyState title={INSIGHTS_TEXT.noEstimates} />
      ) : (
        <Table label={INSIGHTS_TEXT.estimatesLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{words.provider}</Th>
              <Th className="text-right">{words.notes}</Th>
              <Th className="text-right">{words.difference}</Th>
            </tr>
          </thead>
          <tbody>
            {estimates.providers.map((provider) => (
              <Tr key={provider.provider_name}>
                <Td className="font-medium">{provider.provider_name}</Td>
                <Td className="text-right tabular-nums">{formatCount(provider.notes)}</Td>
                <Td className="text-right tabular-nums">{formatMoneyChange(provider.difference)}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}

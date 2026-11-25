import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { Insights } from "@/lib/api/types";
import { formatCount, formatPercent, ratio } from "@/lib/format";
import { INSIGHTS_TEXT } from "../strings";

function MatchedCell({ matched, notes }: { matched: number; notes: number }) {
  const share = ratio(matched, notes);
  return (
    <span className="inline-flex items-center gap-2.5 tabular-nums">
      <span aria-hidden="true" className="inline-block h-1.5 w-27.5 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full rounded-full bg-chart-ok" style={{ width: `${Math.round((share ?? 0) * 100)}%` }} />
      </span>
      {formatPercent(share)}
    </span>
  );
}

export function ProviderTable({ providers }: { providers: Insights["providers"] }) {
  const words = INSIGHTS_TEXT.columns;
  return (
    <Panel>
      <PanelHeader title={INSIGHTS_TEXT.providersTitle} />
      {providers.length === 0 ? (
        <EmptyState title={INSIGHTS_TEXT.noProviders} />
      ) : (
        <Table label={INSIGHTS_TEXT.providersLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{words.provider}</Th>
              <Th className="text-right">{words.notes}</Th>
              <Th>{words.matched}</Th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => (
              <Tr key={provider.provider_name}>
                <Td className="font-medium">{provider.provider_name}</Td>
                <Td className="text-right tabular-nums">{formatCount(provider.notes)}</Td>
                <Td>
                  <MatchedCell matched={provider.matched} notes={provider.notes} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}

import { formatRate } from "@/components/shared/rates";
import { EmptyState } from "@/components/ui/EmptyState";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import type { AgreementSide, ProviderAgreement } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatPercent } from "@/lib/format";
import { QUALITY_TEXT } from "../strings";

interface ProviderAgreementTableProps {
  providers: ProviderAgreement[];
  side: AgreementSide;
}

export function ProviderAgreementTable({ providers, side }: ProviderAgreementTableProps) {
  const words = QUALITY_TEXT.providerColumns;
  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.providersTitle} />
      {providers.length === 0 ? (
        <EmptyState title={QUALITY_TEXT.noCodedNotes} />
      ) : (
        <Table label={QUALITY_TEXT.providersLabel} minWidth="md">
          <thead>
            <tr>
              <Th>{words.provider}</Th>
              <Th className="text-right">{words.notes}</Th>
              <Th>{words.em}</Th>
              <Th className="text-right">{words.f1}</Th>
              <Th>{words.modifiers}</Th>
            </tr>
          </thead>
          <tbody>
            {providers.map((row) => {
              const summary = row[side];
              return (
                <Tr key={row.provider_id}>
                  <Td className="font-medium">{row.provider_name}</Td>
                  <Td className="text-right tabular-nums">{formatCount(summary.notes)}</Td>
                  <Td className="tabular-nums">{formatRate(summary.em)}</Td>
                  <Td className="text-right tabular-nums">
                    {summary.icd_f1 === null ? FORMAT_WORDS.empty : formatPercent(summary.icd_f1)}
                  </Td>
                  <Td className="tabular-nums">{formatRate(summary.modifiers)}</Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </Panel>
  );
}

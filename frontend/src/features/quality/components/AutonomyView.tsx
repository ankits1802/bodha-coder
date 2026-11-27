"use client";

import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { StatusDot } from "@/components/ui/StatusDot";
import { Table, Td, Th, Tr } from "@/components/ui/Table";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getProviderAutonomy, setAutoApprove } from "@/lib/api/quality";
import type { ProviderAutonomy } from "@/lib/api/types";
import { FORMAT_WORDS, formatCount, formatPercent } from "@/lib/format";
import { ELIGIBILITY_TONES } from "../qualityModel";
import { QUALITY_TEXT } from "../strings";

const REMOTE_TEXT = { loading: QUALITY_TEXT.loading, empty: QUALITY_TEXT.noProviders, retry: QUALITY_TEXT.retry };

function percent(share: number | null): string {
  return share === null ? FORMAT_WORDS.empty : formatPercent(share);
}

interface ProviderRowProps {
  provider: ProviderAutonomy;
  canSwitch: boolean;
  pending: boolean;
  onSwitch: (provider: ProviderAutonomy, on: boolean) => void;
}

function ProviderRow({ provider, canSwitch, pending, onSwitch }: ProviderRowProps) {
  const { eligibility } = provider;
  const locked = !canSwitch || pending || (!eligibility.eligible && !provider.auto_approve);
  return (
    <Tr>
      <Td className="font-medium">{provider.name}</Td>
      <Td className="text-right tabular-nums">{eligibility.sample_id ? formatCount(eligibility.notes) : FORMAT_WORDS.empty}</Td>
      <Td className="text-right tabular-nums">{percent(eligibility.em_low)}</Td>
      <Td className="text-right tabular-nums">{percent(eligibility.higher_share)}</Td>
      <Td>
        <StatusDot tone={ELIGIBILITY_TONES[eligibility.reason]}>{QUALITY_TEXT.eligibility[eligibility.reason]}</StatusDot>
      </Td>
      <Td>
        <Toggle
          label={QUALITY_TEXT.autoApproveFor(provider.name)}
          checked={provider.auto_approve}
          disabled={locked}
          onChange={(on) => onSwitch(provider, on)}
        />
      </Td>
    </Tr>
  );
}

export function AutonomyView({ canSwitch }: { canSwitch: boolean }) {
  const providers = useRemote("quality-autonomy", getProviderAutonomy);
  const change = useAction((provider: ProviderAutonomy, on: boolean) => setAutoApprove(provider.id, on));
  const words = QUALITY_TEXT.autonomyColumns;

  async function switchProvider(provider: ProviderAutonomy, on: boolean): Promise<void> {
    if ((await change.run(provider, on)).ok) providers.reload();
  }

  return (
    <Panel>
      <PanelHeader title={QUALITY_TEXT.autonomyTitle} />
      {change.error ? <InlineAlert tone="bad">{change.error}</InlineAlert> : null}
      <RemoteView state={providers.state} text={REMOTE_TEXT} isEmpty={(data) => data.length === 0} onRetry={providers.reload}>
        {(data) => (
          <Table label={QUALITY_TEXT.autonomyLabel} minWidth="lg">
            <thead>
              <tr>
                <Th>{words.provider}</Th>
                <Th className="text-right">{words.notes}</Th>
                <Th className="text-right">{words.low}</Th>
                <Th className="text-right">{words.higher}</Th>
                <Th>{words.eligibility}</Th>
                <Th>{words.autoApprove}</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((provider) => (
                <ProviderRow key={provider.id} provider={provider} canSwitch={canSwitch} pending={change.pending} onSwitch={(item, on) => void switchProvider(item, on)} />
              ))}
            </tbody>
          </Table>
        )}
      </RemoteView>
    </Panel>
  );
}

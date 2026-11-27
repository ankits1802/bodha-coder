"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { TextButton } from "@/components/ui/TextButton";
import { RemoteView } from "@/components/ui/RemoteView";
import { useCanSendTexts } from "@/hooks/useCanSendTexts";
import { useQueryParams } from "@/hooks/useQueryParams";
import { useRemote } from "@/hooks/useRemote";
import type { Provider } from "@/lib/api/types";
import type { SetupOpen } from "@/lib/paths";
import { getPlaces, getProviders } from "@/lib/api/uploads";
import { ImportDialog } from "./ImportDialog";
import { ProviderDialog } from "./ProviderDialog";
import { ProvidersTable } from "./ProvidersTable";
import { PROVIDER_TEXT, SETUP_TEXT } from "./strings";
import { useArrival } from "./useArrival";

interface ProvidersSectionProps {
  missingNpi: number;
  open: SetupOpen | null;
  onOpened: () => void;
  onChanged: () => void;
}

export function ProvidersSection({ missingNpi, open, onOpened, onChanged }: ProvidersSectionProps) {
  const providers = useRemote("setup-providers", getProviders);
  const places = useRemote("setup-places", getPlaces);
  const canSendTexts = useCanSendTexts();
  const query = useQueryParams();
  const onlyMissing = query.get("npi") === "missing";
  const [editing, setEditing] = useState<Provider | "new" | null>(() => (open === "addProvider" ? "new" : null));
  const [importing, setImporting] = useState(open === "importProviders");
  useArrival(open !== null, onOpened);
  const [imported, setImported] = useState<number | null>(null);
  const placeList = places.state.status === "success" ? places.state.data : [];
  const placeNames = new Map(placeList.map((place) => [place.code, place.name]));
  const count = providers.state.status === "success" ? providers.state.data.length : null;

  function changed(): void {
    providers.reload();
    onChanged();
  }

  const toggleMissing = (
    <TextButton onClick={() => query.update({ npi: onlyMissing ? null : "missing" })}>
      {onlyMissing ? PROVIDER_TEXT.showAll : PROVIDER_TEXT.show}
    </TextButton>
  );

  return (
    <Panel aria-label={SETUP_TEXT.sections.providers}>
      <PanelHeader
        title={
          <>
            {SETUP_TEXT.sections.providers}
            {count !== null ? <span className="ml-1.5 font-normal text-tertiary tabular-nums">{count}</span> : null}
          </>
        }
        actions={
          <>
            <Button size="sm" onClick={() => setImporting(true)}>
              {PROVIDER_TEXT.import}
            </Button>
            <Button size="sm" variant="primary" onClick={() => setEditing("new")}>
              {PROVIDER_TEXT.add}
            </Button>
          </>
        }
      />
      {missingNpi > 0 || imported !== null ? (
        <div className="flex flex-col gap-2 px-4 pb-3">
          {missingNpi > 0 ? (
            <InlineAlert tone="warn" action={toggleMissing}>
              {PROVIDER_TEXT.needNpi(missingNpi)}
            </InlineAlert>
          ) : null}
          {imported !== null ? <InlineAlert tone="ok">{PROVIDER_TEXT.importDialog.imported(imported)}</InlineAlert> : null}
        </div>
      ) : null}
      <RemoteView
        state={providers.state}
        text={{ loading: PROVIDER_TEXT.loading, empty: PROVIDER_TEXT.empty, retry: PROVIDER_TEXT.retry }}
        isEmpty={(list) => list.length === 0}
        onRetry={providers.reload}
      >
        {(list) => (
          <ProvidersTable
            providers={onlyMissing ? list.filter((provider) => provider.active && !provider.npi) : list}
            placeNames={placeNames}
            canSendTexts={canSendTexts}
            onEdit={setEditing}
          />
        )}
      </RemoteView>
      {editing !== null ? (
        <ProviderDialog
          provider={editing === "new" ? null : editing}
          places={placeList}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            changed();
          }}
        />
      ) : null}
      {importing ? (
        <ImportDialog
          onClose={() => setImporting(false)}
          onImported={(total) => {
            setImporting(false);
            setImported(total);
            changed();
          }}
        />
      ) : null}
    </Panel>
  );
}

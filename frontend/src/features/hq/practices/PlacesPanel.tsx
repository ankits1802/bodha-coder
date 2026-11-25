"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { Toggle } from "@/components/ui/Toggle";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getHqPlaces, setHqPlace } from "@/lib/api/hq";
import type { HqPlace } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { AddPlaceDialog } from "./AddPlaceDialog";

const words = HQ_TEXT.places;

export function PlacesPanel() {
  const remote = useRemote("hq-places", getHqPlaces);
  const [adding, setAdding] = useState(false);
  const toggle = useAction(setHqPlace);

  async function switchPlace(place: HqPlace, active: boolean): Promise<void> {
    const outcome = await toggle.run(place.code, null, active);
    if (outcome.ok) remote.reload();
  }

  return (
    <Panel aria-label={words.title} className="max-w-140">
      <PanelHeader
        title={words.title}
        actions={
          <Button size="sm" onClick={() => setAdding(true)}>
            {words.add}
          </Button>
        }
      />
      {toggle.error ? (
        <div className="px-4 pb-3">
          <InlineAlert tone="bad">{toggle.error}</InlineAlert>
        </div>
      ) : null}
      <RemoteView
        state={remote.state}
        text={{ loading: words.loading, empty: words.empty, retry: HQ_TEXT.retry }}
        isEmpty={(places) => places.length === 0}
        onRetry={remote.reload}
      >
        {(places) => (
          <ul className="m-0 list-none p-0">
            {places.map((place) => (
              <li key={place.code} className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4">
                <span className={place.active ? "text-label" : "text-tertiary"}>
                  {place.name} <span className="text-tertiary tabular-nums">{place.code}</span>
                </span>
                <Toggle
                  label={`${place.name} (${place.code})`}
                  checked={place.active}
                  disabled={toggle.pending}
                  onChange={(on) => void switchPlace(place, on)}
                />
              </li>
            ))}
          </ul>
        )}
      </RemoteView>
      {adding ? (
        <AddPlaceDialog
          onClose={() => setAdding(false)}
          onAdded={() => {
            setAdding(false);
            remote.reload();
          }}
        />
      ) : null}
    </Panel>
  );
}

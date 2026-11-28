"use client";

import { InlineAlert } from "@/components/ui/InlineAlert";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RemoteView } from "@/components/ui/RemoteView";
import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import { useRemote } from "@/hooks/useRemote";
import { getAppearance } from "@/lib/api/account";
import type { Appearance } from "@/lib/api/types";
import {
  APPEARANCE_KEEP_SECONDS,
  APPEARANCE_KEY,
  applyAppearance,
  MOTION_CHOICES,
  TEXT_SIZES,
  THEMES,
} from "@/lib/appearance";
import { SECURITY_TEXT } from "./strings";
import { useAppearanceSaver } from "./useAppearanceSaver";

const TEXT = SECURITY_TEXT.appearance;
const REMOTE_TEXT = { loading: TEXT.loading, empty: "", retry: TEXT.retry };

function segmentsOf<V extends string>(values: readonly V[], labels: Record<V, string>): Segment<V>[] {
  return values.map((value) => ({ value, label: labels[value] }));
}

const THEME_SEGMENTS = segmentsOf(THEMES, TEXT.themes);
const SIZE_SEGMENTS = segmentsOf(TEXT_SIZES, TEXT.textSizes);
const MOTION_SEGMENTS = segmentsOf(MOTION_CHOICES, TEXT.motions);

interface ChoiceRowProps<V extends string> {
  label: string;
  value: V;
  segments: Segment<V>[];
  onChange: (value: V) => void;
}

function ChoiceRow<V extends string>({ label, value, segments, onChange }: ChoiceRowProps<V>) {
  return (
    <div className="flex min-h-12 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-hairline px-4 py-2 text-body">
      <span aria-hidden="true">{label}</span>
      <SegmentedControl label={label} value={value} segments={segments} onChange={onChange} />
    </div>
  );
}

export function AppearancePanel() {
  const remote = useRemote(APPEARANCE_KEY, getAppearance, APPEARANCE_KEEP_SECONDS);
  const saver = useAppearanceSaver();

  function change(next: Appearance): void {
    applyAppearance(next);
    remote.replace(next);
    saver.save(next);
  }

  return (
    <Panel aria-label={TEXT.title} className="max-w-180">
      <PanelHeader title={TEXT.title} />
      <RemoteView state={remote.state} text={REMOTE_TEXT} onRetry={remote.reload}>
        {(appearance) => (
          <>
            <ChoiceRow
              label={TEXT.theme}
              value={appearance.theme}
              segments={THEME_SEGMENTS}
              onChange={(theme) => change({ ...appearance, theme })}
            />
            <ChoiceRow
              label={TEXT.textSize}
              value={appearance.text_size}
              segments={SIZE_SEGMENTS}
              onChange={(size) => change({ ...appearance, text_size: size })}
            />
            <ChoiceRow
              label={TEXT.motion}
              value={appearance.reduce_motion}
              segments={MOTION_SEGMENTS}
              onChange={(motion) => change({ ...appearance, reduce_motion: motion })}
            />
            {saver.error ? (
              <div className="border-t border-hairline px-4 py-3">
                <InlineAlert tone="bad">{saver.error}</InlineAlert>
              </div>
            ) : null}
          </>
        )}
      </RemoteView>
    </Panel>
  );
}

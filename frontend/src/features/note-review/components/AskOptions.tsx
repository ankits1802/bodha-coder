import { SegmentedControl, type Segment } from "@/components/ui/SegmentedControl";
import type { Channel } from "@/lib/api/types";
import { isOfferedChannel } from "@/lib/channels";
import { CHANNEL_LABELS } from "@/lib/labels";
import { REVIEW_TEXT } from "../strings";

interface AskOptionsProps {
  channel: Channel;
  onChannel: (channel: Channel) => void;
  canSendTexts: boolean;
  hold: boolean;
  onHold: (hold: boolean) => void;
}

const CHANNEL_SEGMENTS: readonly Segment<Channel>[] = [
  { value: "sms", label: CHANNEL_LABELS.sms },
  { value: "email", label: CHANNEL_LABELS.email },
];

function HoldChoice({ checked, label, onSelect }: { checked: boolean; label: string; onSelect: () => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 border-t border-hairline px-4 py-3.5 first:border-t-0">
      <input type="radio" name="hold" checked={checked} onChange={onSelect} className="size-4.5 flex-none accent-label" />
      <span className="font-medium">{label}</span>
    </label>
  );
}

export function AskOptions({ channel, onChannel, canSendTexts, hold, onHold }: AskOptionsProps) {
  const words = REVIEW_TEXT.askDialog;
  return (
    <>
      <div>
        <p className="mt-0 mb-2 ml-1 text-subhead font-semibold text-secondary">{words.sendBy}</p>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-panel bg-surface px-4 py-3.5 shadow-panel">
          <SegmentedControl<Channel>
            label={words.sendBy}
            value={channel}
            onChange={onChannel}
            segments={CHANNEL_SEGMENTS.filter((segment) => isOfferedChannel(segment.value, canSendTexts))}
          />
          <span className="text-secondary">{words.secureLink}</span>
        </div>
      </div>
      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-2 ml-1 text-subhead font-semibold text-secondary">{words.whileWaiting}</legend>
        <div className="overflow-hidden rounded-panel bg-surface shadow-panel">
          <HoldChoice checked={hold} label={words.hold} onSelect={() => onHold(true)} />
          <HoldChoice checked={!hold} label={words.noHold} onSelect={() => onHold(false)} />
        </div>
      </fieldset>
    </>
  );
}

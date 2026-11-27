import { Field } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { Toggle } from "@/components/ui/Toggle";
import type { Channel } from "@/lib/api/types";
import { CHANNEL_LABELS } from "@/lib/labels";
import { ProviderTextInput, type ProviderInputHandlers } from "./ProviderTextInput";
import { PROVIDER_TEXT } from "./strings";

interface ProviderMoreFieldsProps extends ProviderInputHandlers {
  canSendTexts: boolean;
  onActive: (active: boolean) => void;
}

const CHANNELS: readonly Channel[] = ["email", "sms"];

export function ProviderMoreFields({ canSendTexts, onActive, ...handlers }: ProviderMoreFieldsProps) {
  const words = PROVIDER_TEXT.dialog;
  const { draft, onChange } = handlers;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <ProviderTextInput {...handlers} field="specialty" label={words.specialty} optional />
      {canSendTexts ? (
        <>
          <Field label={words.channel}>
            {(control) => (
              <Select
                {...control}
                value={draft.channel}
                options={CHANNELS.map((channel) => ({ value: channel, label: CHANNEL_LABELS[channel] }))}
                onChange={(value) => onChange("channel", value)}
              />
            )}
          </Field>
          <ProviderTextInput {...handlers} field="phone" label={words.phone} type="tel" optional={draft.channel !== "sms"} />
        </>
      ) : null}
      <div className="flex items-center justify-between gap-3 sm:col-span-2">
        <span aria-hidden="true" className="text-subhead font-medium">
          {words.active}
        </span>
        <Toggle label={words.active} checked={draft.active} onChange={onActive} />
      </div>
    </div>
  );
}

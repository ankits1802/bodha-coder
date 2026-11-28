import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { Select } from "@/components/ui/Select";
import type { ClaimTransport, ClaimUsage, IdQualifier } from "@/lib/api/types";
import { ID_QUALIFIERS, type ConnectionDraft, type ConnectionErrors, type DraftChange } from "./connectionModel";
import { CLEARINGHOUSE_TEXT } from "./strings";

const USAGES: ClaimUsage[] = ["test", "production"];
const TRANSPORTS: ClaimTransport[] = ["sftp", "portal"];
const QUALIFIER_OPTIONS = ID_QUALIFIERS.map((value) => ({ value, label: value }));

interface ConnectionIdentityFieldsProps {
  draft: ConnectionDraft;
  errors: ConnectionErrors;
  onChange: DraftChange;
}

export function ConnectionIdentityFields({ draft, errors, onChange }: ConnectionIdentityFieldsProps) {
  const words = CLEARINGHOUSE_TEXT;
  return (
    <>
      <Field label={words.name} error={errors.name} className="sm:col-span-2">
        {(control) => <Input {...control} maxLength={80} value={draft.name} onChange={(event) => onChange({ name: event.target.value })} />}
      </Field>
      <div className="flex flex-col gap-1.5">
        <span aria-hidden="true" className="text-subhead font-medium text-label">
          {words.usage}
        </span>
        <SegmentedControl<ClaimUsage>
          label={words.usage}
          value={draft.usage}
          segments={USAGES.map((value) => ({ value, label: words.usages[value] }))}
          onChange={(usage) => onChange({ usage })}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <span aria-hidden="true" className="text-subhead font-medium text-label">
          {words.transport}
        </span>
        <SegmentedControl<ClaimTransport>
          label={words.transport}
          value={draft.transport}
          segments={TRANSPORTS.map((value) => ({ value, label: words.transports[value] }))}
          onChange={(transport) => onChange({ transport })}
        />
      </div>
      <Field label={words.senderQualifier}>
        {(control) => (
          <Select<IdQualifier>
            {...control}
            value={draft.sender_qualifier}
            options={QUALIFIER_OPTIONS}
            onChange={(sender_qualifier) => onChange({ sender_qualifier })}
          />
        )}
      </Field>
      <Field label={words.senderId} error={errors.sender_id}>
        {(control) => <Input {...control} maxLength={15} value={draft.sender_id} onChange={(event) => onChange({ sender_id: event.target.value })} />}
      </Field>
      <Field label={words.receiverQualifier}>
        {(control) => (
          <Select<IdQualifier>
            {...control}
            value={draft.receiver_qualifier}
            options={QUALIFIER_OPTIONS}
            onChange={(receiver_qualifier) => onChange({ receiver_qualifier })}
          />
        )}
      </Field>
      <Field label={words.receiverId} error={errors.receiver_id}>
        {(control) => (
          <Input {...control} maxLength={15} value={draft.receiver_id} onChange={(event) => onChange({ receiver_id: event.target.value })} />
        )}
      </Field>
      <Field label={words.receiverName} error={errors.receiver_name} className="sm:col-span-2">
        {(control) => (
          <Input {...control} maxLength={60} value={draft.receiver_name} onChange={(event) => onChange({ receiver_name: event.target.value })} />
        )}
      </Field>
    </>
  );
}

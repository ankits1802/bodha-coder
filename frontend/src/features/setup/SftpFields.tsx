import { Field } from "@/components/ui/Field";
import { Input, TextArea } from "@/components/ui/Input";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { AuthKind } from "@/lib/api/types";
import type { ConnectionDraft, ConnectionErrors, DraftChange } from "./connectionModel";
import { CLEARINGHOUSE_TEXT } from "./strings";

const AUTH_KINDS: AuthKind[] = ["password", "key"];

interface SftpFieldsProps {
  draft: ConnectionDraft;
  errors: ConnectionErrors;
  secretSaved: boolean;
  onChange: DraftChange;
}

export function SftpFields({ draft, errors, secretSaved, onChange }: SftpFieldsProps) {
  const words = CLEARINGHOUSE_TEXT;
  const placeholder = secretSaved ? words.savedSecret : undefined;
  return (
    <>
      <Field label={words.host} error={errors.host}>
        {(control) => <Input {...control} maxLength={253} autoComplete="off" value={draft.host} onChange={(event) => onChange({ host: event.target.value })} />}
      </Field>
      <Field label={words.port} error={errors.port}>
        {(control) => <Input {...control} inputMode="numeric" value={draft.port} onChange={(event) => onChange({ port: event.target.value })} />}
      </Field>
      <Field label={words.username} error={errors.username}>
        {(control) => (
          <Input {...control} maxLength={128} autoComplete="off" value={draft.username} onChange={(event) => onChange({ username: event.target.value })} />
        )}
      </Field>
      <div className="flex flex-col gap-1.5">
        <span aria-hidden="true" className="text-subhead font-medium text-label">
          {words.authKind}
        </span>
        <SegmentedControl<AuthKind>
          label={words.authKind}
          value={draft.auth_kind}
          segments={AUTH_KINDS.map((value) => ({ value, label: words.authKinds[value] }))}
          onChange={(auth_kind) => onChange({ auth_kind, secret: "" })}
        />
      </div>
      {draft.auth_kind === "password" ? (
        <Field label={words.password} error={errors.secret} className="sm:col-span-2">
          {(control) => (
            <Input
              {...control}
              type="password"
              autoComplete="new-password"
              placeholder={placeholder}
              value={draft.secret}
              onChange={(event) => onChange({ secret: event.target.value })}
            />
          )}
        </Field>
      ) : (
        <Field label={words.privateKey} error={errors.secret} className="sm:col-span-2">
          {(control) => (
            <TextArea
              {...control}
              rows={5}
              spellCheck={false}
              autoComplete="off"
              placeholder={placeholder}
              value={draft.secret}
              onChange={(event) => onChange({ secret: event.target.value })}
              className="text-footnote"
            />
          )}
        </Field>
      )}
      <Field label={words.outboundFolder} error={errors.outbound_folder}>
        {(control) => (
          <Input {...control} maxLength={255} value={draft.outbound_folder} onChange={(event) => onChange({ outbound_folder: event.target.value })} />
        )}
      </Field>
      <Field label={words.inboundFolder} error={errors.inbound_folder}>
        {(control) => (
          <Input {...control} maxLength={255} value={draft.inbound_folder} onChange={(event) => onChange({ inbound_folder: event.target.value })} />
        )}
      </Field>
    </>
  );
}

import type { SsoAdmin } from "@/lib/api/types";
import { toggled, type SsoDraft } from "./ssoDraft";
import { SSO_TEXT } from "./strings";
import { ToggleRow } from "./ToggleRow";

interface RequiredSectionProps {
  draft: SsoDraft;
  admins: readonly SsoAdmin[];
  onChange: (next: Partial<SsoDraft>) => void;
}

export function RequiredSection({ draft, admins, onChange }: RequiredSectionProps) {
  return (
    <section aria-label={SSO_TEXT.required} className="flex flex-col gap-1 border-t border-hairline px-4 py-4">
      <ToggleRow label={SSO_TEXT.required} checked={draft.required} onChange={(required) => onChange({ required })} />
      {draft.required ? (
        <div className="flex flex-col gap-1 pt-2">
          <h3 className="m-0 text-subhead font-medium text-label">{SSO_TEXT.breakGlass}</h3>
          {admins.map((admin) => (
            <ToggleRow
              key={admin.id}
              label={admin.name}
              toggleLabel={SSO_TEXT.breakGlassFor(admin.name)}
              checked={draft.breakGlass.includes(admin.id)}
              disabled={!admin.ready && !draft.breakGlass.includes(admin.id)}
              detail={
                <span className="text-subhead text-secondary">{admin.ready ? admin.email : SSO_TEXT.notReady(admin.email)}</span>
              }
              onChange={(on) => onChange({ breakGlass: toggled(draft.breakGlass, admin.id, on) })}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

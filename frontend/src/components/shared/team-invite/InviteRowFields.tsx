import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import type { InviteRow, RowErrors } from "./inviteRows";
import { INVITE_ROWS_TEXT } from "./strings";

export const ROW_GRID = "grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_9rem_auto] sm:items-start";

interface InviteRowFieldsProps {
  row: InviteRow;
  number: number;
  errors: RowErrors;
  removable: boolean;
  onChange: (row: InviteRow) => void;
  onRemove: () => void;
}

function Problem({ id, text }: { id: string; text: string | undefined | null }) {
  if (!text) return null;
  return (
    <span id={id} className="text-footnote text-bad-text">
      {text}
    </span>
  );
}

export function InviteRowFields({ row, number, errors, removable, onChange, onRemove }: InviteRowFieldsProps) {
  const words = INVITE_ROWS_TEXT;
  const ids = { name: `invite-${row.id}-name`, email: `invite-${row.id}-email`, failure: `invite-${row.id}-failure` };
  const described = (field: "name" | "email") =>
    [errors[field] ? ids[field] : null, row.failure ? ids.failure : null].filter(Boolean).join(" ") || undefined;
  return (
    <li className="flex flex-col gap-1">
      <div className={ROW_GRID}>
        <span className="flex flex-col gap-1">
          <Input
            aria-label={words.nameFor(number)}
            autoComplete="off"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={described("name")}
            value={row.name}
            onChange={(event) => onChange({ ...row, name: event.target.value, failure: null })}
          />
          <Problem id={ids.name} text={errors.name} />
        </span>
        <span className="flex flex-col gap-1">
          <Input
            type="email"
            autoComplete="off"
            aria-label={words.emailFor(number)}
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={described("email")}
            value={row.email}
            onChange={(event) => onChange({ ...row, email: event.target.value, failure: null })}
          />
          <Problem id={ids.email} text={errors.email} />
        </span>
        <Select<PracticeRole>
          label={words.roleFor(number)}
          value={row.role}
          options={PRACTICE_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] }))}
          onChange={(role) => onChange({ ...row, role })}
        />
        <Button size="sm" variant="plain" className="justify-self-start" disabled={!removable} aria-label={words.removeFor(number)} onClick={onRemove}>
          {words.remove}
        </Button>
      </div>
      <Problem id={ids.failure} text={row.failure} />
    </li>
  );
}

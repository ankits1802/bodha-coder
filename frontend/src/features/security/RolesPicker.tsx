"use client";

import { useId, useState } from "react";
import { Chevron } from "@/components/ui/Chevron";
import type { PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { SECURITY_TEXT } from "./strings";

interface RolesPickerProps {
  value: Set<PracticeRole>;
  onToggle: (role: PracticeRole, on: boolean) => void;
}

function summaryOf(value: Set<PracticeRole>): string {
  const chosen = PRACTICE_ROLES.filter((role) => value.has(role)).map((role) => ROLE_LABELS[role]);
  return chosen.length > 0 ? chosen.join(", ") : SECURITY_TEXT.noRoles;
}

export function RolesPicker({ value, onToggle }: RolesPickerProps) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((current) => !current)}
        className="flex min-h-13 w-full cursor-pointer items-center justify-between gap-4 px-4.5 text-left text-body"
      >
        <span>{SECURITY_TEXT.twoStepFor}</span>
        <span className="inline-flex items-center gap-2 text-secondary">
          {summaryOf(value)}
          <Chevron className={`flex-none text-chevron transition-transform ${open ? "rotate-90" : ""}`} />
        </span>
      </button>
      {open ? (
        <fieldset id={listId} className="m-0 grid gap-1 border-0 px-4.5 pb-3 sm:grid-cols-3">
          <legend className="sr-only">{SECURITY_TEXT.rolesLabel}</legend>
          {PRACTICE_ROLES.map((role) => (
            <label key={role} className="flex min-h-9 cursor-pointer items-center gap-2.5 text-body">
              <input
                type="checkbox"
                checked={value.has(role)}
                onChange={(event) => onToggle(role, event.target.checked)}
                className="size-4 accent-label"
              />
              {ROLE_LABELS[role]}
            </label>
          ))}
        </fieldset>
      ) : null}
    </div>
  );
}

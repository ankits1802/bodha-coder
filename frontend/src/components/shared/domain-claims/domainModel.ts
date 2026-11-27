import type { SelectOption } from "@/components/ui/Select";
import type { AdminMailbox, DomainJoinMode, PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { DOMAIN_TEXT } from "./strings";

export interface PracticeOption {
  id: string;
  name: string;
}

export const ADMIN_MAILBOXES: readonly AdminMailbox[] = ["admin", "administrator", "hostmaster", "postmaster", "webmaster"];
export const JOIN_MODES: readonly DomainJoinMode[] = ["off", "request", "auto"];
export const DEFAULT_JOIN_ROLE: PracticeRole = "viewer";

export const MAILBOX_OPTIONS: readonly SelectOption<AdminMailbox>[] = ADMIN_MAILBOXES.map((mailbox) => ({
  value: mailbox,
  label: DOMAIN_TEXT.mailboxes[mailbox],
}));

export const MODE_OPTIONS: readonly SelectOption<DomainJoinMode>[] = JOIN_MODES.map((mode) => ({
  value: mode,
  label: DOMAIN_TEXT.modes[mode],
}));

export const AUTO_ROLE_OPTIONS: readonly SelectOption<PracticeRole>[] = PRACTICE_ROLES.filter((role) => role !== "admin").map((role) => ({
  value: role,
  label: ROLE_LABELS[role],
}));

export function joinRoleFor(mode: DomainJoinMode, role: PracticeRole): PracticeRole {
  return mode === "auto" && role === "admin" ? DEFAULT_JOIN_ROLE : role;
}

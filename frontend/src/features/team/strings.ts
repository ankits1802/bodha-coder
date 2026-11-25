import type { RoleFilter } from "./teamModel";

export type ConfirmKind = "block" | "unblock" | "reset";

export const TEAM_TEXT = {
  title: "Team",
  loading: "Loading team",
  empty: "No members in this group",
  retry: "Try again",
  seats: (used: number, total: number) => `${used} of ${total} seats`,
  invite: "Invite",
  filterLabel: "Show",
  filters: {
    all: "Everyone",
    coder: "Coders",
    cdi: "Specialists",
    compliance: "Compliance",
    biller: "Billers",
    "admin-viewer": "Admin & viewer",
  } satisfies Record<RoleFilter, string>,
  tableLabel: "Team members",
  columns: { name: "Name", role: "Role", twoStep: "Two-step", lastActive: "Last active", more: "More" },
  twoStepOn: "On",
  twoStepOff: "Off",
  you: "You",
  roleFor: (name: string) => `Role for ${name}`,
  moreFor: (name: string) => `More for ${name}`,
  menu: { reset: "Reset two-step", resend: "Resend invite", block: "Block", unblock: "Unblock" },
  resent: (email: string) => `Invite sent to ${email}`,
  roleChanged: (name: string) => `${name} must sign in again`,
  confirm: {
    cancel: "Cancel",
    titles: {
      block: (name: string) => `Block ${name}?`,
      unblock: (name: string) => `Unblock ${name}?`,
      reset: (name: string) => `Reset two-step for ${name}?`,
    } satisfies Record<ConfirmKind, (name: string) => string>,
    descriptions: {
      block: "They are signed out and can no longer sign in.",
      unblock: "They can sign in again.",
      reset: "They are signed out and set up two-step again at next sign-in.",
    } satisfies Record<ConfirmKind, string>,
    actions: { block: "Block", unblock: "Unblock", reset: "Reset" } satisfies Record<ConfirmKind, string>,
  },
  inviteDialog: {
    title: "Invite to the team",
    name: "Name",
    email: "Email",
    role: "Role",
    cancel: "Cancel",
    send: "Send invite",
    errors: { name: "Enter a name", email: "Enter a valid email" },
  },
} as const;

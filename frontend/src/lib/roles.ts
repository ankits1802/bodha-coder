import type { PracticeRole, Role, User } from "@/lib/api/types";
import { organizationPath } from "@/lib/paths";

export type SessionUser = Pick<User, "role" | "billing_only" | "organizations">;

export const PLAN_PATH = "/settings/plan";

export const PRACTICE_ROLES: readonly PracticeRole[] = ["admin", "coder", "cdi", "compliance", "biller", "viewer"];
const HQ: readonly Role[] = ["hq"];
const ADMINS: readonly Role[] = ["admin"];
const UPLOADERS: readonly Role[] = ["admin", "coder"];
const NOTE_READERS: readonly Role[] = ["admin", "coder", "cdi", "compliance", "biller"];
const DECIDERS: readonly Role[] = ["admin", "coder", "cdi", "compliance"];
const APPROVERS: readonly Role[] = ["admin", "coder", "compliance"];
const ASKERS: readonly Role[] = ["admin", "coder", "cdi"];
const ASSIGNERS: readonly Role[] = ["admin", "coder", "cdi"];
const COMPLIANCE: readonly Role[] = ["admin", "compliance"];
const BILLERS: readonly Role[] = ["admin", "biller"];
const INSIGHT_READERS: readonly Role[] = ["admin", "compliance", "viewer"];

export type Area =
  | "today"
  | "inbox"
  | "upload"
  | "queue"
  | "compliance"
  | "billing"
  | "insights"
  | "settings"
  | "setup"
  | "team"
  | "plan"
  | "security"
  | "accessLog"
  | "usage"
  | "account"
  | "help"
  | "hq";

export type Action =
  | "decide"
  | "approve"
  | "ask"
  | "complianceDecision"
  | "retry"
  | "flag"
  | "manageNotes"
  | "voidAnyNote"
  | "restoreNote"
  | "readAccessLog"
  | "manageSecurity"
  | "assign"
  | "assignAnyone"
  | "search"
  | "sign";

const AREA_ROLES: Record<Area, readonly Role[]> = {
  today: PRACTICE_ROLES,
  inbox: NOTE_READERS,
  upload: UPLOADERS,
  queue: NOTE_READERS,
  compliance: COMPLIANCE,
  billing: BILLERS,
  insights: INSIGHT_READERS,
  settings: ADMINS,
  setup: ADMINS,
  team: ADMINS,
  plan: ADMINS,
  security: ADMINS,
  accessLog: COMPLIANCE,
  usage: ADMINS,
  account: PRACTICE_ROLES,
  help: PRACTICE_ROLES,
  hq: HQ,
};

const ACTION_ROLES: Record<Action, readonly Role[]> = {
  decide: DECIDERS,
  approve: APPROVERS,
  ask: ASKERS,
  complianceDecision: COMPLIANCE,
  retry: UPLOADERS,
  flag: DECIDERS,
  manageNotes: UPLOADERS,
  voidAnyNote: ADMINS,
  restoreNote: ADMINS,
  readAccessLog: COMPLIANCE,
  manageSecurity: ADMINS,
  assign: ASSIGNERS,
  assignAnyone: ADMINS,
  search: NOTE_READERS,
  sign: DECIDERS,
};

export function canUse(role: Role | null | undefined, area: Area): boolean {
  return role != null && AREA_ROLES[area].includes(role);
}

export function canDo(role: Role | null | undefined, action: Action): boolean {
  return role != null && ACTION_ROLES[action].includes(role);
}

const BILLING_ONLY_AREAS: readonly Area[] = ["settings", "plan"];

export function canReach(user: SessionUser | null | undefined, area: Area): boolean {
  if (user == null || !canUse(user.role, area)) return false;
  return !user.billing_only || BILLING_ONLY_AREAS.includes(area);
}

export function reachableHref(user: SessionUser | null | undefined, area: Area, href: string): string | null {
  return canReach(user, area) ? href : null;
}

export function canSearch(user: SessionUser | null | undefined): boolean {
  return user != null && !user.billing_only && canDo(user.role, "search");
}

export function canSearchPlatform(user: SessionUser | null | undefined): boolean {
  return user != null && canUse(user.role, "hq");
}

export function isOrganizationAdmin(user: SessionUser | null | undefined, organizationId: string): boolean {
  return user?.organizations?.some((choice) => choice.id === organizationId) ?? false;
}

export function canOpenPath(user: SessionUser, pathname: string): boolean {
  if (!user.billing_only || pathname === PLAN_PATH) return true;
  return (user.organizations ?? []).some((choice) => pathname === organizationPath(choice.id, "plan"));
}

const HOMES: Partial<Record<Role, string>> = { hq: "/hq", biller: "/billing", compliance: "/compliance" };

export function homeFor(user: SessionUser): string {
  const paying = user.organizations?.[0];
  if (user.billing_only && user.role !== "admin" && paying) return organizationPath(paying.id, "plan");
  if (user.billing_only) return PLAN_PATH;
  return HOMES[user.role] ?? "/today";
}

export const HQ_IDLE_MINUTES = 15;

export function idleMinutesFor(role: Role, practiceIdleMinutes: number | null | undefined): number {
  if (role === "hq" || practiceIdleMinutes == null) return HQ_IDLE_MINUTES;
  return practiceIdleMinutes;
}

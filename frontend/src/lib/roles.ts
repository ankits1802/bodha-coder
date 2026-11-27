import type { PracticeRole, Role, User } from "@/lib/api/types";

export type SessionUser = Pick<User, "role" | "billing_only">;

export const PLAN_PATH = "/plan";

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
  | "setup"
  | "team"
  | "plan"
  | "security"
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
  | "manageSecurity"
  | "assign"
  | "assignAnyone"
  | "search";

const AREA_ROLES: Record<Area, readonly Role[]> = {
  today: PRACTICE_ROLES,
  inbox: NOTE_READERS,
  upload: UPLOADERS,
  queue: NOTE_READERS,
  compliance: COMPLIANCE,
  billing: BILLERS,
  insights: INSIGHT_READERS,
  setup: ADMINS,
  team: ADMINS,
  plan: ADMINS,
  security: PRACTICE_ROLES,
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
  manageSecurity: ADMINS,
  assign: ASSIGNERS,
  assignAnyone: ADMINS,
  search: NOTE_READERS,
};

export function canUse(role: Role | null | undefined, area: Area): boolean {
  return role != null && AREA_ROLES[area].includes(role);
}

export function canDo(role: Role | null | undefined, action: Action): boolean {
  return role != null && ACTION_ROLES[action].includes(role);
}

const BILLING_ONLY_AREAS: readonly Area[] = ["plan"];

export function canReach(user: SessionUser | null | undefined, area: Area): boolean {
  if (user == null || !canUse(user.role, area)) return false;
  return !user.billing_only || BILLING_ONLY_AREAS.includes(area);
}

export function canSearch(user: SessionUser | null | undefined): boolean {
  return user != null && !user.billing_only && canDo(user.role, "search");
}

export function canSearchPlatform(user: SessionUser | null | undefined): boolean {
  return user != null && canUse(user.role, "hq");
}

export function canOpenPath(user: SessionUser, pathname: string): boolean {
  return !user.billing_only || pathname === PLAN_PATH;
}

const HOMES: Partial<Record<Role, string>> = { hq: "/hq", biller: "/billing", compliance: "/compliance" };

export function homeFor(user: SessionUser): string {
  if (user.billing_only) return PLAN_PATH;
  return HOMES[user.role] ?? "/today";
}

export const HQ_IDLE_MINUTES = 15;

export function idleMinutesFor(role: Role, practiceIdleMinutes: number | null | undefined): number {
  if (role === "hq" || practiceIdleMinutes == null) return HQ_IDLE_MINUTES;
  return practiceIdleMinutes;
}

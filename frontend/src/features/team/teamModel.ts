import type { Role, TeamMember } from "@/lib/api/types";
import { addDays } from "@/lib/dates";
import type { DayRange } from "@/lib/paths";

export type RoleFilter = "all" | "coder" | "cdi" | "compliance" | "biller" | "admin-viewer";

export const ROLE_FILTERS: readonly RoleFilter[] = ["all", "coder", "cdi", "compliance", "biller", "admin-viewer"];

const FILTER_ROLES: Record<Exclude<RoleFilter, "all">, readonly Role[]> = {
  coder: ["coder"],
  cdi: ["cdi"],
  compliance: ["compliance"],
  biller: ["biller"],
  "admin-viewer": ["admin", "viewer"],
};

export function isRoleFilter(value: string | null): value is RoleFilter {
  return value !== null && (ROLE_FILTERS as readonly string[]).includes(value);
}

export function inFilter(member: TeamMember, filter: RoleFilter): boolean {
  return filter === "all" || FILTER_ROLES[filter].includes(member.role);
}

export function countIn(members: TeamMember[], filter: RoleFilter): number {
  return members.filter((member) => inFilter(member, filter)).length;
}

export function seatsUsed(members: TeamMember[]): number {
  return members.filter((member) => member.status !== "blocked").length;
}

export const ACTIVITY_DAYS = 30;

export function activityRange(today: string): DayRange {
  return { start: addDays(today, 1 - ACTIVITY_DAYS) ?? today, end: today };
}

import type { StatusTone } from "@/components/ui/StatusDot";
import type { HqTeamMember, MemberStatus } from "@/lib/api/types";

export type HqConfirmKind = "deactivate" | "reactivate";
export type HqMemberAction = "resend" | HqConfirmKind;

export const STATUS_TONES: Record<MemberStatus, StatusTone> = { invited: "neutral", active: "ok", blocked: "bad" };

export function hqMemberActions(member: Pick<HqTeamMember, "status">, isSelf: boolean): HqMemberAction[] {
  if (isSelf) return [];
  if (member.status === "blocked") return ["reactivate"];
  return member.status === "invited" ? ["resend", "deactivate"] : ["deactivate"];
}

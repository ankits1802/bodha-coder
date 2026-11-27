import type { Channel, Lane, MemberStatus, Plan, PracticeStatus, Role } from "@/lib/api/types";

export const ROLE_LABELS: Record<Role, string> = {
  hq: "Platform admin",
  admin: "Admin",
  coder: "Coder",
  cdi: "CDI specialist",
  compliance: "Compliance",
  biller: "Biller",
  viewer: "Viewer",
};

export const LANE_LABELS: Record<Lane, string> = {
  approve: "Ready to approve",
  coder: "Needs a coder",
  provider: "Waiting on provider",
  compliance: "Compliance",
};

export const LANE_ORDER: readonly Lane[] = ["approve", "coder", "provider", "compliance"];

export const CHANNEL_LABELS: Record<Channel, string> = {
  email: "Email",
  sms: "Text message",
};

export const MEMBER_STATUS_LABELS: Record<MemberStatus, string> = {
  invited: "Invited",
  active: "Active",
  blocked: "Blocked",
};

export const PLAN_LABELS: Record<Plan, string> = {
  trial: "Trial",
  essentials: "Essentials",
  professional: "Professional",
  enterprise: "Enterprise",
};

export const PRACTICE_STATUS_LABELS: Record<PracticeStatus, string> = {
  trial: "Trial",
  active: "Active",
  ended: "Ended",
  blocked: "Blocked",
};

export const VISIT_TYPES = ["Established patient", "New patient"] as const;

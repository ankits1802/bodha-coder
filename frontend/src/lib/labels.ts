import type { Channel, Lane, LaneReason, MemberStatus, Plan, PracticeStatus, ProviderReason, ReturnReason, Role } from "@/lib/api/types";

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

const LANE_REASONS: Record<LaneReason, true> = {
  flagged: true,
  levels_too_high: true,
  audit_risk: true,
  waiting_on_provider: true,
  code_changes: true,
  questions: true,
  matches: true,
  returned: true,
};

export function isLane(value: string | null): value is Lane {
  return value !== null && (LANE_ORDER as readonly string[]).includes(value);
}

export function isLaneReason(value: string | null): value is LaneReason {
  return value !== null && Object.hasOwn(LANE_REASONS, value);
}

export const PROVIDER_REASON_LABELS: Record<ProviderReason, string> = {
  questions: "Questions to send",
  waiting_on_provider: "Waiting on provider",
};

export type LaneViewKey = Exclude<Lane, "provider"> | ProviderReason;

export interface LaneView {
  key: LaneViewKey;
  lane: Lane;
  reason: ProviderReason | null;
  label: string;
}

export const LANE_VIEWS: readonly LaneView[] = [
  { key: "approve", lane: "approve", reason: null, label: LANE_LABELS.approve },
  { key: "coder", lane: "coder", reason: null, label: LANE_LABELS.coder },
  { key: "questions", lane: "provider", reason: "questions", label: PROVIDER_REASON_LABELS.questions },
  { key: "waiting_on_provider", lane: "provider", reason: "waiting_on_provider", label: PROVIDER_REASON_LABELS.waiting_on_provider },
  { key: "compliance", lane: "compliance", reason: null, label: LANE_LABELS.compliance },
];

export const RETURN_REASONS: readonly ReturnReason[] = [
  "level_not_supported",
  "documentation_missing",
  "coding_error",
  "ask_provider",
  "payer_policy",
  "other",
];

export const RETURN_REASON_LABELS: Record<ReturnReason, string> = {
  level_not_supported: "Level not supported",
  documentation_missing: "Documentation missing",
  coding_error: "Coding error",
  ask_provider: "Ask the provider",
  payer_policy: "Payer policy",
  other: "Other",
};

export function isReturnReason(value: unknown): value is ReturnReason {
  return typeof value === "string" && Object.hasOwn(RETURN_REASON_LABELS, value);
}

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
  closed: "Closed",
  purged: "Purged",
};

export const VISIT_TYPES = ["Established patient", "New patient"] as const;

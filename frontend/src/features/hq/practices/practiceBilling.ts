import type { StatusTone } from "@/components/ui/StatusDot";
import type { BillingStatus, HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";

const BILLING_TONES: Record<BillingStatus, StatusTone> = {
  pending: "neutral",
  active: "ok",
  past_due: "warn",
  canceled: "bad",
  expired: "bad",
};

const words = HQ_TEXT.practices.billing;

export function billingView(practice: Pick<HqPractice, "billing_provider" | "billing_status">): { tone: StatusTone; label: string } | null {
  if (!practice.billing_provider || !practice.billing_status) return null;
  const label = words.line(words.statuses[practice.billing_status], words.providers[practice.billing_provider]);
  return { tone: BILLING_TONES[practice.billing_status], label };
}

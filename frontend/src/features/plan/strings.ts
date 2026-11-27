import { PLAN_CHOOSER_TEXT } from "@/components/shared/plan-chooser/strings";

export const PLAN_TEXT = {
  ...PLAN_CHOOSER_TEXT,
  title: "Plan and billing",
  loading: "Loading plan",
  retry: "Try again",
  summaryLabel: "Current plan",
  ended: "Your practice's plan has ended",
  billedBy: {
    label: "Billing",
    title: (organization: string) => `Billed through ${organization}`,
    open: (organization: string) => `Open ${organization}`,
  },
} as const;

import type { PlanStatus } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { PLAN_BANNER_TEXT } from "./strings";

export interface BannerView {
  tone: "ok" | "warn";
  text: string;
  action: string;
}

export const DISMISS_STORAGE_KEY = "bodha.planBanner.dismissedOn";
const TRIAL_WARNING_DAYS = 3;

const words = PLAN_BANNER_TEXT;

export function bannerFor(status: PlanStatus): BannerView | null {
  if (status.standing === "past_due") {
    return { tone: "warn", text: words.pastDue(formatCalendarDay(status.renews_on, "year")), action: words.fixPayment };
  }
  if (status.standing === "trial" && status.trial_days_left !== null) {
    const tone = status.trial_days_left <= TRIAL_WARNING_DAYS ? "warn" : "ok";
    return { tone, text: words.trialLeft(status.trial_days_left), action: words.choosePlan };
  }
  return null;
}

export function readDismissal(): string | null {
  try {
    return window.localStorage.getItem(DISMISS_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function saveDismissal(day: string): void {
  try {
    window.localStorage.setItem(DISMISS_STORAGE_KEY, day);
  } catch {
    return;
  }
}

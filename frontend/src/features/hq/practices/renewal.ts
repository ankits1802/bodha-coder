import type { HqPractice } from "@/lib/api/types";
import { addDays, addMonths, isoDateInZone } from "@/lib/dates";

export type RenewalPreset = "days14" | "month1" | "month3" | "month6" | "year1" | "noEnd";

export const RENEWAL_PRESETS: readonly RenewalPreset[] = ["days14", "month1", "month3", "month6", "year1", "noEnd"];

const MONTHS: Record<Exclude<RenewalPreset, "days14" | "noEnd">, number> = { month1: 1, month3: 3, month6: 6, year1: 12 };

export interface RenewalChoice {
  preset: RenewalPreset | null;
  until: string | null;
}

export function practiceToday(practice: Pick<HqPractice, "time_zone">, moment: Date = new Date()): string {
  return isoDateInZone(moment, practice.time_zone);
}

export function renewalBase(practice: Pick<HqPractice, "renews_on">, today: string): string {
  return practice.renews_on && practice.renews_on > today ? practice.renews_on : today;
}

export function presetUntil(preset: RenewalPreset, base: string): string | null {
  if (preset === "noEnd") return null;
  if (preset === "days14") return addDays(base, 14);
  return addMonths(base, MONTHS[preset]);
}

export function choosePreset(preset: RenewalPreset, base: string): RenewalChoice {
  return { preset, until: presetUntil(preset, base) };
}

export function canRenew(choice: RenewalChoice, today: string): boolean {
  if (choice.preset === "noEnd") return true;
  return choice.until !== null && choice.until > today;
}

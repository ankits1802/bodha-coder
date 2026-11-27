import type { HqPractice, NewPractice, Plan, PracticeStatus, PracticeUpdate } from "@/lib/api/types";
import { isIsoDate } from "@/lib/dates";
import { isEmail } from "@/lib/validation";
import { HQ_TEXT } from "../strings";

export const PLANS: readonly Plan[] = ["trial", "basic", "professional", "enterprise"];
export const STATUSES: readonly PracticeStatus[] = ["trial", "active", "ended", "blocked"];
const MAX_SEATS = 10_000;

const errors = HQ_TEXT.practices.form.errors;

export function seatsError(seats: string): string | null {
  const value = Number(seats);
  return Number.isInteger(value) && value >= 1 && value <= MAX_SEATS ? null : errors.seats;
}

export interface NewPracticeDraft {
  name: string;
  admin_name: string;
  admin_email: string;
  plan: Plan;
  seats: string;
  time_zone: string;
}

export type NewPracticeErrors = Partial<Record<keyof NewPracticeDraft, string>>;

export function validateNewPractice(draft: NewPracticeDraft): NewPracticeErrors {
  const found: NewPracticeErrors = {};
  if (draft.name.trim().length < 2) found.name = errors.name;
  if (!draft.admin_name.trim()) found.admin_name = errors.adminName;
  if (!isEmail(draft.admin_email)) found.admin_email = errors.adminEmail;
  const seats = seatsError(draft.seats);
  if (seats) found.seats = seats;
  return found;
}

export function newPracticeBody(draft: NewPracticeDraft): NewPractice {
  return {
    name: draft.name.trim(),
    admin_name: draft.admin_name.trim(),
    admin_email: draft.admin_email.trim(),
    plan: draft.plan,
    seats: Number(draft.seats),
    time_zone: draft.time_zone,
  };
}

export interface PracticeEditDraft {
  name: string;
  status: PracticeStatus;
  plan: Plan;
  seats: string;
  renews_on: string;
  time_zone: string;
}

export function editDraftFrom(practice: HqPractice): PracticeEditDraft {
  return {
    name: practice.name,
    status: practice.status,
    plan: practice.plan,
    seats: String(practice.seats),
    renews_on: practice.renews_on ?? "",
    time_zone: practice.time_zone,
  };
}

export function practiceChanges(practice: HqPractice, draft: PracticeEditDraft): PracticeUpdate {
  const update: PracticeUpdate = {};
  if (draft.name.trim().length >= 2 && draft.name.trim() !== practice.name) update.name = draft.name.trim();
  if (draft.status !== practice.status) update.status = draft.status;
  if (draft.plan !== practice.plan) update.plan = draft.plan;
  if (Number(draft.seats) !== practice.seats) update.seats = Number(draft.seats);
  if (isIsoDate(draft.renews_on) && draft.renews_on !== practice.renews_on) update.renews_on = draft.renews_on;
  if (draft.renews_on === "" && practice.renews_on !== null) update.renews_on = null;
  if (draft.time_zone !== practice.time_zone) update.time_zone = draft.time_zone;
  return update;
}

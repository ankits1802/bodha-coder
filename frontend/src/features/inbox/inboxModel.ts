import type { InboxEntry, InboxKind } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { TEAM_PATH } from "@/lib/paths";
import { PLAN_PATH } from "@/lib/roles";
import { INBOX_TEXT } from "./strings";

const words = INBOX_TEXT.sentences;
const TRAINING_PATH = "/training";

const SENTENCES: Record<InboxKind, (entry: InboxEntry) => string> = {
  provider_answered: (entry) => words.providerAnswered(entry.actor_name, entry.payload.questions ?? 0),
  level_disagreed: (entry) => words.levelDisagreed(entry.actor_name),
  request_expired: (entry) => (entry.payload.purpose === "level_change" ? words.levelRequestExpired : words.requestExpired),
  mentioned: (entry) => words.mentioned(entry.actor_name),
  training_assigned: (entry) => words.trainingAssigned(entry.actor_name, entry.payload.notes ?? 0),
  payment_failed: (entry) => words.paymentFailed(formatCalendarDay(entry.payload.access_until ?? null, "year")),
  plan_ending: (entry) => words.planEnding(formatCalendarDay(entry.payload.ends_on ?? null, "year")),
  compliance_returned: (entry) => words.complianceReturned(entry.actor_name),
  join_requested: (entry) => words.joinRequested(entry.actor_name),
};

const FIXED_TARGETS: Partial<Record<InboxKind, string>> = {
  training_assigned: TRAINING_PATH,
  payment_failed: PLAN_PATH,
  plan_ending: PLAN_PATH,
  join_requested: TEAM_PATH,
};

const NOTE_TABS: Partial<Record<InboxKind, string>> = { mentioned: "history" };

export function inboxSentence(entry: InboxEntry): string {
  return SENTENCES[entry.kind](entry);
}

export function inboxTarget(entry: InboxEntry): string | null {
  const fixed = FIXED_TARGETS[entry.kind];
  if (fixed) return fixed;
  if (!entry.note_id) return null;
  const path = `/notes/${encodeURIComponent(entry.note_id)}`;
  const tab = NOTE_TABS[entry.kind];
  return tab ? `${path}?tab=${tab}` : path;
}

export function inboxMeta(entry: InboxEntry): string | null {
  if (!entry.patient_name) return null;
  return entry.service_date ? INBOX_TEXT.meta(entry.patient_name, formatCalendarDay(entry.service_date)) : entry.patient_name;
}

export function isUnread(entry: InboxEntry): boolean {
  return entry.read_at === null;
}

import type { StatusTone } from "@/components/ui/StatusDot";
import type { EmAction, Lane, LaneReason, NoteStatus, NoteSummary } from "@/lib/api/types";
import { LANE_LABELS } from "@/lib/labels";
import { SHARED_TEXT } from "./strings";

export interface NoteStatusView {
  tone: StatusTone;
  label: string;
}

const REASON_TONES: Record<LaneReason, StatusTone> = {
  flagged: "warn",
  levels_too_high: "bad",
  audit_risk: "bad",
  waiting_on_provider: "warn",
  code_changes: "dark",
  questions: "warn",
  matches: "ok",
};

const EM_ACTION_TONES: Partial<Record<EmAction, StatusTone>> = {
  lower: "bad",
  raise: "low",
  replace: "bad",
};

const LANE_TONES: Record<Lane, StatusTone> = {
  approve: "ok",
  coder: "dark",
  provider: "warn",
  compliance: "bad",
};

export const LANE_DOT_TONES = LANE_TONES;

export const DELETABLE_STATUSES: readonly NoteStatus[] = ["queued", "ready", "failed", "approved"];
export const ASSIGNABLE_STATUSES: readonly NoteStatus[] = ["queued", "reading", "ready", "failed"];

type StatusFields = Pick<NoteSummary, "status" | "lane" | "lane_reason" | "headline"> & { em_action?: EmAction | null };

function toneOf(note: StatusFields): StatusTone {
  if (note.lane_reason === "code_changes" && note.em_action) return EM_ACTION_TONES[note.em_action] ?? REASON_TONES.code_changes;
  if (note.lane_reason) return REASON_TONES[note.lane_reason];
  return note.lane ? LANE_TONES[note.lane] : "neutral";
}

export function noteStatus(note: StatusFields): NoteStatusView {
  const words = SHARED_TEXT.noteStatus;
  if (note.status === "queued" || note.status === "reading") return { tone: "neutral", label: words.reading };
  if (note.status === "failed") return { tone: "bad", label: words.failed };
  if (note.status === "approved" || note.status === "exported") return { tone: "ok", label: words[note.status] };
  return { tone: toneOf(note), label: note.headline ?? (note.lane ? LANE_LABELS[note.lane] : words.ready) };
}

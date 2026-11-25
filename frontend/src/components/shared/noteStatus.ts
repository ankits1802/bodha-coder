import type { StatusTone } from "@/components/ui/StatusDot";
import type { Lane, NoteSummary } from "@/lib/api/types";
import { LANE_LABELS } from "@/lib/labels";
import { SHARED_TEXT } from "./strings";

export interface NoteStatusView {
  tone: StatusTone;
  label: string;
}

const HEADLINE_TONES: Record<string, StatusTone> = {
  "Billed too high": "bad",
  "Billed too low": "low",
  "Wrong visit code family": "bad",
  "Diagnosis missing": "dark",
  "Matches the note": "ok",
  "Waiting on provider": "warn",
  "Flagged for compliance": "warn",
  "High audit risk": "bad",
};

const LANE_TONES: Record<Lane, StatusTone> = {
  approve: "ok",
  coder: "dark",
  provider: "warn",
  compliance: "bad",
};

export const LANE_DOT_TONES = LANE_TONES;

export function noteStatus(note: Pick<NoteSummary, "status" | "lane" | "headline">): NoteStatusView {
  const words = SHARED_TEXT.noteStatus;
  if (note.status === "queued" || note.status === "reading") return { tone: "neutral", label: words.reading };
  if (note.status === "failed") return { tone: "bad", label: words.failed };
  if (note.status === "approved" || note.status === "exported") return { tone: "ok", label: words[note.status] };
  const label = note.headline ?? (note.lane ? LANE_LABELS[note.lane] : words.ready);
  const byHeadline = note.headline ? HEADLINE_TONES[note.headline] : undefined;
  return { tone: byHeadline ?? (note.lane ? LANE_TONES[note.lane] : "neutral"), label };
}

export function isOpenForReview(note: Pick<NoteSummary, "status">): boolean {
  return note.status === "ready";
}

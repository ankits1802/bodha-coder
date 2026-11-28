import type { StatusTone } from "@/components/ui/StatusDot";
import type { EhrDocument, EhrPullRun } from "@/lib/api/types";
import { EHR_TEXT } from "./strings";

const words = EHR_TEXT;

export function runTone(run: EhrPullRun): StatusTone {
  if (run.outcome === "failed" || run.outcome === "interrupted") return "bad";
  if (run.outcome === "running" || run.outcome === "partial") return "neutral";
  return run.refused > 0 ? "warn" : "ok";
}

export function runSummary(run: EhrPullRun): string {
  const outcome = words.outcomes[run.outcome];
  return run.reason ? `${outcome}: ${words.runReasons[run.reason]}` : outcome;
}

export function documentTone(document: EhrDocument): StatusTone {
  if (document.outcome === "refused") return "bad";
  return document.outcome === "duplicate" ? "neutral" : "ok";
}

export function documentSummary(document: EhrDocument): string {
  const outcome = words.documentOutcomes[document.outcome];
  return document.reason ? `${outcome}: ${words.documentReasons[document.reason]}` : outcome;
}

import type { StatusTone } from "@/components/ui/StatusDot";
import type { ClaimChecks, ClaimEdit, PayerFlag, PayerFlagSeverity } from "@/lib/api/types";
import { CLAIM_CHECK_TEXT } from "./strings";

export interface ClaimCheckItem {
  key: string;
  tone: StatusTone;
  status: string;
  codes: string[];
  detail: string | null;
}

const WORDS = CLAIM_CHECK_TEXT;

const SEVERITY_TONES: Record<PayerFlagSeverity, StatusTone> = { denial: "bad", risk: "warn", reminder: "neutral" };

function editItem(edit: ClaimEdit, index: number): ClaimCheckItem {
  const key = `${edit.kind}:${index}`;
  if (edit.kind === "mue") {
    return { key, tone: "bad", status: WORDS.overLimit(edit.limit), codes: [WORDS.units(edit.code, edit.units)], detail: null };
  }
  if (edit.kind === "aoc") {
    return { key, tone: "bad", status: WORDS.noPrimary, codes: [edit.code], detail: null };
  }
  const codes = [edit.column1, edit.column2];
  if (edit.bypassed_by) return { key, tone: "ok", status: WORDS.bypassed(edit.bypassed_by), codes, detail: null };
  return { key, tone: "bad", status: WORDS.together, codes, detail: edit.modifier_allowed ? WORDS.modifierAllowed : null };
}

function flagItem(flag: PayerFlag, index: number): ClaimCheckItem {
  return {
    key: `${flag.rule}:${index}`,
    tone: SEVERITY_TONES[flag.severity],
    status: WORDS.rules[flag.rule],
    codes: flag.codes,
    detail: null,
  };
}

function notice(key: string, tone: StatusTone, status: string): ClaimCheckItem {
  return { key, tone, status, codes: [], detail: null };
}

export function claimCheckItems(checks: ClaimChecks): ClaimCheckItem[] {
  const items = [...checks.edits.map(editItem), ...checks.payer_flags.map(flagItem)];
  const notices: ClaimCheckItem[] = [];
  if (!checks.ncci.covers) notices.push(notice("ncci", "neutral", WORDS.notLoaded(checks.ncci.quarter)));
  if (checks.payer === null) notices.push(notice("payer", "neutral", WORDS.payerNotSet));
  if (items.length === 0 && checks.ncci.covers) notices.unshift(notice("clean", "ok", WORDS.clean));
  return [...items, ...notices];
}

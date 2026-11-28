import type { Charge } from "@/lib/api/types";
import { CHARGE_TEXT } from "./strings";

const CODE_PATTERN = /^(\d{4}[0-9A-Z]|[A-Z]\d{4})$/;
const AMOUNT_PATTERN = /^(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?$/;
const MAX_CENTS = 9_999_999;
const CENTS_PER_DOLLAR = 100;

export interface ChargeDraft {
  code: string;
  amount: string;
}

export type ChargeErrors = Partial<Record<keyof ChargeDraft, string>>;

export function chargeDraftFrom(charge: Charge | null): ChargeDraft {
  return { code: charge?.code ?? "", amount: charge ? (charge.cents / CENTS_PER_DOLLAR).toFixed(2) : "" };
}

export function chargeCode(draft: ChargeDraft): string {
  return draft.code.trim().toUpperCase();
}

export function centsFrom(amount: string): number | null {
  const clean = amount.trim().replace(/^\$\s*/, "");
  if (!AMOUNT_PATTERN.test(clean)) return null;
  const [whole = "0", fraction = ""] = clean.replaceAll(",", "").split(".");
  const cents = Number(whole) * CENTS_PER_DOLLAR + Number(fraction.padEnd(2, "0"));
  return cents > 0 && cents <= MAX_CENTS ? cents : null;
}

export function validateCharge(draft: ChargeDraft): ChargeErrors {
  const words = CHARGE_TEXT.dialog.errors;
  const errors: ChargeErrors = {};
  if (!CODE_PATTERN.test(chargeCode(draft))) errors.code = words.code;
  if (centsFrom(draft.amount) === null) errors.amount = words.amount;
  return errors;
}

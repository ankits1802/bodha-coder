import type { Payer, PayerInput, PlanType } from "@/lib/api/types";
import { PAYER_TEXT } from "./strings";

export const PLAN_TYPES: readonly PlanType[] = ["commercial", "medicare", "medicaid", "other"];

export interface PayerDraft {
  name: string;
  payer_id: string;
  plan_type: PlanType;
  active: boolean;
}

export type PayerErrors = Partial<Record<"name" | "payer_id", string>>;

const PAYER_ID = /^[A-Z0-9-]{2,15}$/;

export function payerDraftFrom(payer: Payer | null): PayerDraft {
  return {
    name: payer?.name ?? "",
    payer_id: payer?.payer_id ?? "",
    plan_type: payer?.plan_type ?? "commercial",
    active: payer?.active ?? true,
  };
}

export function validatePayer(draft: PayerDraft): PayerErrors {
  const words = PAYER_TEXT.dialog.errors;
  const errors: PayerErrors = {};
  if (!draft.name.trim()) errors.name = words.name;
  const payerId = draft.payer_id.trim().toUpperCase();
  if (payerId && !PAYER_ID.test(payerId)) errors.payer_id = words.payerId;
  return errors;
}

export function payerInputFrom(draft: PayerDraft): PayerInput {
  const payerId = draft.payer_id.trim().toUpperCase();
  return { name: draft.name.trim(), payer_id: payerId || null, plan_type: draft.plan_type, active: draft.active };
}

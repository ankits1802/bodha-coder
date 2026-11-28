import type { ClaimDetailsInput, ClaimDetailsView, PatientSex, Relationship } from "@/lib/api/types";
import { CLAIM_DETAILS_TEXT } from "./strings";

export const SELF: Relationship = "18";
export const RELATIONSHIPS: readonly Relationship[] = ["18", "01", "19", "G8"];
export const SEXES: readonly PatientSex[] = ["F", "M", "U"];

const STATE_PATTERN = /^[A-Za-z]{2}$/;
const ZIP_PATTERN = /^\d{5}(-?\d{4})?$/;
const MEMBER_PATTERN = /^[A-Za-z0-9-]{2,80}$/;
const REQUIRED = ["patient_last", "patient_first", "street", "city"] as const;

export interface DetailsDraft {
  patient_last: string;
  patient_first: string;
  patient_birth_date: string | null;
  patient_sex: PatientSex | null;
  street: string;
  street_2: string;
  city: string;
  state: string;
  zip_code: string;
  relationship: Relationship;
  member_id: string;
  group_number: string;
  subscriber_last: string;
  subscriber_first: string;
  payer: string;
}

export type DetailsErrors = Partial<Record<keyof DetailsDraft, string>>;
export type DetailsChange = (change: Partial<DetailsDraft>) => void;

export function detailsDraftFrom(view: ClaimDetailsView): DetailsDraft {
  const known = view.details ?? view.suggested;
  return {
    patient_last: known?.patient_last ?? "",
    patient_first: known?.patient_first ?? "",
    patient_birth_date: known?.patient_birth_date ?? null,
    patient_sex: known?.patient_sex ?? null,
    street: known?.street ?? "",
    street_2: known?.street_2 ?? "",
    city: known?.city ?? "",
    state: known?.state ?? "",
    zip_code: known?.zip_code ?? "",
    relationship: known?.relationship ?? SELF,
    member_id: known?.member_id ?? "",
    group_number: known?.group_number ?? "",
    subscriber_last: known?.subscriber_last ?? "",
    subscriber_first: known?.subscriber_first ?? "",
    payer: "",
  };
}

export function readName(view: ClaimDetailsView): string | null {
  return view.suggested?.patient_name ?? null;
}

export function validateDetails(draft: DetailsDraft, needsPayer: boolean): DetailsErrors {
  const words = CLAIM_DETAILS_TEXT.errors;
  const errors: DetailsErrors = {};
  for (const field of REQUIRED) if (!draft[field].trim()) errors[field] = words.required;
  if (!draft.patient_birth_date) errors.patient_birth_date = words.birthDate;
  if (!draft.patient_sex) errors.patient_sex = words.required;
  if (!STATE_PATTERN.test(draft.state.trim())) errors.state = words.state;
  if (!ZIP_PATTERN.test(draft.zip_code.trim())) errors.zip_code = words.zip;
  if (!MEMBER_PATTERN.test(draft.member_id.trim())) errors.member_id = words.memberId;
  if (needsPayer && !draft.payer) errors.payer = words.required;
  if (draft.relationship !== SELF && !draft.subscriber_last.trim()) errors.subscriber_last = words.required;
  if (draft.relationship !== SELF && !draft.subscriber_first.trim()) errors.subscriber_first = words.required;
  return errors;
}

export function detailsInputFrom(draft: DetailsDraft): ClaimDetailsInput {
  const isSelf = draft.relationship === SELF;
  return {
    patient_last: draft.patient_last.trim(),
    patient_first: draft.patient_first.trim(),
    patient_birth_date: draft.patient_birth_date ?? "",
    patient_sex: draft.patient_sex ?? "U",
    street: draft.street.trim(),
    street_2: draft.street_2.trim() || null,
    city: draft.city.trim(),
    state: draft.state.trim().toUpperCase(),
    zip_code: draft.zip_code.trim(),
    relationship: draft.relationship,
    member_id: draft.member_id.trim().toUpperCase(),
    group_number: draft.group_number.trim() || null,
    subscriber_last: isSelf ? null : draft.subscriber_last.trim(),
    subscriber_first: isSelf ? null : draft.subscriber_first.trim(),
  };
}

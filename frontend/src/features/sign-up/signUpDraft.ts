import type { IdentitySignupRequest, NewPracticeRequest, SignupRequest } from "@/lib/api/types";
import { isEmail } from "@/lib/validation";
import { SIGN_UP_TEXT } from "./strings";

export interface SignUpDraft {
  name: string;
  practice_name: string;
  email: string;
  time_zone: string;
  agreed: boolean;
}

export type SignUpField = keyof SignUpDraft;
export type SignUpErrors = Partial<Record<SignUpField, string>>;

const NAME_MAX = 120;
const PRACTICE_MIN = 2;
const PRACTICE_MAX = 200;
const errors = SIGN_UP_TEXT.errors;

export function signUpErrors(draft: SignUpDraft, fields: readonly SignUpField[]): SignUpErrors {
  const found: SignUpErrors = {};
  const name = draft.name.trim();
  const practice = draft.practice_name.trim();
  if (!name || name.length > NAME_MAX) found.name = errors.name;
  if (practice.length < PRACTICE_MIN || practice.length > PRACTICE_MAX) found.practice_name = errors.practiceName;
  if (!isEmail(draft.email)) found.email = errors.email;
  if (!draft.agreed) found.agreed = errors.agreed;
  return Object.fromEntries(Object.entries(found).filter(([field]) => fields.includes(field as SignUpField)));
}

export function signupRequest(draft: SignUpDraft): SignupRequest {
  return {
    name: draft.name.trim(),
    practice_name: draft.practice_name.trim(),
    email: draft.email.trim(),
    time_zone: draft.time_zone,
    agreed: true,
  };
}

export function identitySignupRequest(draft: SignUpDraft): IdentitySignupRequest {
  return { name: draft.name.trim(), practice_name: draft.practice_name.trim(), time_zone: draft.time_zone, agreed: true };
}

export function newPracticeRequest(draft: SignUpDraft): NewPracticeRequest {
  return { practice_name: draft.practice_name.trim(), time_zone: draft.time_zone, agreed: true };
}

export function blankDraft(timeZone: string, values: Partial<SignUpDraft> = {}): SignUpDraft {
  return { name: "", practice_name: "", email: "", time_zone: timeZone, agreed: false, ...values };
}

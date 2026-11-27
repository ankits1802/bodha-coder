import type { Channel, Provider, ProviderInput } from "@/lib/api/types";
import { usableChannel } from "@/lib/channels";
import { isEmail, isNpiShaped } from "@/lib/validation";
import { credentialDraftFrom, detailsFrom, validateCredentials, type CredentialDraft, type CredentialErrors } from "./credentialForm";
import { PROVIDER_TEXT } from "./strings";

export interface ProviderDraft {
  name: string;
  credential: string;
  specialty: string;
  npi: string;
  place_code: string;
  email: string;
  phone: string;
  channel: Channel;
  active: boolean;
  details: CredentialDraft;
}

export type ProviderTextField = Exclude<keyof ProviderDraft, "active" | "details">;
export type ProviderErrors = Partial<Record<ProviderTextField, string>> & CredentialErrors;

export function draftFrom(provider: Provider | null, canSendTexts: boolean): ProviderDraft {
  return {
    name: provider?.name ?? "",
    credential: provider?.credential ?? "MD",
    specialty: provider?.specialty ?? "",
    npi: provider?.npi ?? "",
    place_code: provider?.place_code ?? "",
    email: provider?.email ?? "",
    phone: provider?.phone ?? "",
    channel: usableChannel(provider?.channel ?? "email", canSendTexts),
    active: provider?.active ?? true,
    details: credentialDraftFrom(provider?.details),
  };
}

export function validateProvider(draft: ProviderDraft): ProviderErrors {
  const words = PROVIDER_TEXT.dialog.errors;
  const errors: ProviderErrors = { ...validateCredentials(draft.details) };
  if (!draft.name.trim()) errors.name = words.name;
  if (draft.npi.trim() && !isNpiShaped(draft.npi)) errors.npi = words.npi;
  if (draft.email.trim() && !isEmail(draft.email)) errors.email = words.email;
  if (draft.channel === "email" && !draft.email.trim()) errors.email = words.emailNeeded;
  if (draft.channel === "sms" && !draft.phone.trim()) errors.phone = words.phoneNeeded;
  return errors;
}

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function inputFrom(draft: ProviderDraft): ProviderInput {
  return {
    name: draft.name.trim(),
    credential: draft.credential,
    specialty: optional(draft.specialty),
    npi: optional(draft.npi),
    place_code: optional(draft.place_code),
    email: optional(draft.email),
    phone: optional(draft.phone),
    channel: draft.channel,
    active: draft.active,
    details: detailsFrom(draft.details),
  };
}

const MAIN_FIELDS: readonly string[] = ["name", "credential", "npi", "place_code", "email"];

export function hidesError(errors: ProviderErrors): boolean {
  return Object.keys(errors).some((field) => !MAIN_FIELDS.includes(field));
}

export function touchedErrors(errors: ProviderErrors, touched: readonly string[]): ProviderErrors {
  return Object.fromEntries(Object.entries(errors).filter(([field]) => touched.includes(field))) as ProviderErrors;
}

import type { Channel, Provider, ProviderInput } from "@/lib/api/types";
import { isEmail, isNpiShaped } from "@/lib/validation";
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
}

export type ProviderTextField = Exclude<keyof ProviderDraft, "active">;
export type ProviderErrors = Partial<Record<ProviderTextField, string>>;

export function draftFrom(provider: Provider | null): ProviderDraft {
  return {
    name: provider?.name ?? "",
    credential: provider?.credential ?? "MD",
    specialty: provider?.specialty ?? "",
    npi: provider?.npi ?? "",
    place_code: provider?.place_code ?? "",
    email: provider?.email ?? "",
    phone: provider?.phone ?? "",
    channel: provider?.channel ?? "email",
    active: provider?.active ?? true,
  };
}

export function validateProvider(draft: ProviderDraft): ProviderErrors {
  const words = PROVIDER_TEXT.dialog.errors;
  const errors: ProviderErrors = {};
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
  };
}

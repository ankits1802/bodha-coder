import type { SsoIdentityProvider, SsoNewPersonRole, SsoSettingsRequest, SsoVersion } from "@/lib/api/types";

export interface SsoDraft {
  provider: SsoIdentityProvider | null;
  claimIds: string[];
  emailAttribute: string;
  nameAttribute: string;
  createPeople: boolean;
  newPersonRole: SsoNewPersonRole;
  required: boolean;
  breakGlass: string[];
  mfaContext: string;
}

export const NEW_PERSON_ROLES: readonly SsoNewPersonRole[] = ["coder", "cdi", "compliance", "biller", "viewer"];
const DEFAULT_ROLE: SsoNewPersonRole = "viewer";

export function draftFrom(current: SsoVersion | null | undefined): SsoDraft {
  return {
    provider: current?.identity_provider ?? null,
    claimIds: current ? [...current.claim_ids] : [],
    emailAttribute: current?.email_attribute ?? "",
    nameAttribute: current?.name_attribute ?? "",
    createPeople: current?.create_people ?? false,
    newPersonRole: current?.new_person_role ?? DEFAULT_ROLE,
    required: current?.required ?? false,
    breakGlass: current ? [...current.break_glass] : [],
    mfaContext: current?.mfa_context ?? "",
  };
}

export function withImported(draft: SsoDraft, imported: SsoIdentityProvider): SsoDraft {
  const kept = draft.provider?.certificates ?? [];
  const added = imported.certificates.filter((item) => !kept.some((known) => known.value === item.value));
  return { ...draft, provider: { ...imported, certificates: [...kept, ...added] } };
}

export function withoutCertificate(draft: SsoDraft, value: string): SsoDraft {
  if (!draft.provider) return draft;
  const certificates = draft.provider.certificates.filter((item) => item.value !== value);
  return { ...draft, provider: { ...draft.provider, certificates } };
}

export function toggled(values: readonly string[], value: string, on: boolean): string[] {
  const without = values.filter((item) => item !== value);
  return on ? [...without, value] : without;
}

function optional(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === "" ? null : trimmed;
}

export function requestFrom(draft: SsoDraft): SsoSettingsRequest | null {
  const provider = draft.provider;
  if (!provider || provider.certificates.length === 0) return null;
  return {
    identity_provider: {
      entity_id: provider.entity_id,
      sso_url: provider.sso_url,
      certificates: provider.certificates.map((item) => item.value),
      metadata_url: provider.metadata_url,
    },
    claim_ids: draft.claimIds,
    email_attribute: optional(draft.emailAttribute),
    name_attribute: optional(draft.nameAttribute),
    create_people: draft.createPeople,
    new_person_role: draft.newPersonRole,
    required: draft.required,
    break_glass: draft.required ? draft.breakGlass : [],
    mfa_context: optional(draft.mfaContext),
  };
}

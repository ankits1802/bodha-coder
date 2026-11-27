import type { BillsUnder, ProviderDetails } from "@/lib/api/types";
import { isNpiShaped } from "@/lib/validation";
import { PROVIDER_TEXT } from "./strings";

export interface CredentialDraft {
  taxonomy_code: string;
  license_number: string;
  license_state: string;
  dea_number: string;
  bills_under: BillsUnder | "";
  group_npi: string;
  supervising_physician: string;
  signature_on_file: boolean;
}

export type CredentialTextField = Exclude<keyof CredentialDraft, "signature_on_file">;
export type CredentialErrors = Partial<Record<CredentialTextField, string>>;

const TAXONOMY_CODE = /^[0-9A-Z]{9}X$/;
const STATE_CODE = /^[A-Z]{2}$/;
const DEA_SHAPE = /^[A-Z][A-Z9]\d{7}$/;

export function credentialDraftFrom(details: ProviderDetails | undefined): CredentialDraft {
  return {
    taxonomy_code: details?.taxonomy_code ?? "",
    license_number: details?.license_number ?? "",
    license_state: details?.license_state ?? "",
    dea_number: details?.dea_number ?? "",
    bills_under: details?.bills_under ?? "",
    group_npi: details?.group_npi ?? "",
    supervising_physician: details?.supervising_physician ?? "",
    signature_on_file: details?.signature_on_file ?? false,
  };
}

function upper(value: string): string {
  return value.trim().toUpperCase();
}

export function validateCredentials(draft: CredentialDraft): CredentialErrors {
  const words = PROVIDER_TEXT.dialog.credentials.errors;
  const errors: CredentialErrors = {};
  if (draft.taxonomy_code.trim() && !TAXONOMY_CODE.test(upper(draft.taxonomy_code))) errors.taxonomy_code = words.taxonomy;
  if (draft.license_state.trim() && !STATE_CODE.test(upper(draft.license_state))) errors.license_state = words.state;
  if (draft.license_number.trim() && !draft.license_state.trim()) errors.license_state = words.stateNeeded;
  if (draft.license_state.trim() && !draft.license_number.trim()) errors.license_number = words.numberNeeded;
  if (draft.dea_number.trim() && !DEA_SHAPE.test(upper(draft.dea_number))) errors.dea_number = words.dea;
  if (draft.group_npi.trim() && !isNpiShaped(draft.group_npi)) errors.group_npi = words.groupNpi;
  return errors;
}

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function detailsFrom(draft: CredentialDraft): ProviderDetails {
  return {
    taxonomy_code: optional(upper(draft.taxonomy_code)),
    license_number: optional(upper(draft.license_number)),
    license_state: optional(upper(draft.license_state)),
    dea_number: optional(upper(draft.dea_number)),
    bills_under: draft.bills_under || null,
    group_npi: optional(draft.group_npi),
    supervising_physician: optional(draft.supervising_physician),
    signature_on_file: draft.signature_on_file,
  };
}

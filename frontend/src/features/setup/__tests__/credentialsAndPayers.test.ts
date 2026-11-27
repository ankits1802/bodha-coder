import { describe, expect, it } from "vitest";
import type { Provider } from "@/lib/api/types";
import { credentialDraftFrom, detailsFrom, validateCredentials, type CredentialDraft } from "../credentialForm";
import { payerDraftFrom, payerInputFrom, validatePayer } from "../payerForm";
import { draftFrom, inputFrom, validateProvider } from "../providerForm";

const EMPTY: CredentialDraft = credentialDraftFrom(undefined);

function draft(change: Partial<CredentialDraft>): CredentialDraft {
  return { ...EMPTY, ...change };
}

describe("credentialing details", () => {
  it("accepts a taxonomy code in any case and a DEA number of two letters and seven digits", () => {
    expect(validateCredentials(draft({ taxonomy_code: "207q00000x", dea_number: "bj6125341" }))).toEqual({});
  });

  it("names each field that cannot be right", () => {
    const errors = validateCredentials(
      draft({ taxonomy_code: "207Q0000X", dea_number: "B1234567", group_npi: "12345", license_state: "Texas", license_number: "DO-778" }),
    );
    expect(errors).toEqual({
      taxonomy_code: "Use the 10-character taxonomy code ending in X",
      dea_number: "Use 2 letters and 7 digits",
      group_npi: "Use the 10-digit NPI",
      license_state: "Use the 2-letter state code",
    });
  });

  it("asks for the license number and its state together", () => {
    expect(validateCredentials(draft({ license_number: "DO-778" }))).toEqual({ license_state: "Add the state that issued the license" });
    expect(validateCredentials(draft({ license_state: "TX" }))).toEqual({ license_number: "Add the license number" });
  });

  it("sends codes in capitals and leaves blank fields empty", () => {
    const details = detailsFrom(draft({ taxonomy_code: " 207q00000x ", license_number: "do-778", license_state: "tx", signature_on_file: true }));
    expect(details).toEqual({
      taxonomy_code: "207Q00000X",
      license_number: "DO-778",
      license_state: "TX",
      dea_number: null,
      bills_under: null,
      group_npi: null,
      supervising_physician: null,
      signature_on_file: true,
    });
  });

  it("travels with the provider and blocks saving while a detail is wrong", () => {
    const provider: Provider = {
      id: "prov-1",
      name: "Amara Okafor",
      credential: "DO",
      specialty: null,
      npi: null,
      place_code: null,
      email: "okafor@clinic.example.com",
      phone: null,
      channel: "email",
      active: true,
      details: { ...detailsFrom(EMPTY), bills_under: "group", group_npi: "1234567893" },
    };
    const providerDraft = draftFrom(provider);
    expect(inputFrom(providerDraft).details).toEqual(provider.details);
    const wrong = { ...providerDraft, details: { ...providerDraft.details, dea_number: "AB12" } };
    expect(validateProvider(wrong)).toEqual({ dea_number: "Use 2 letters and 7 digits" });
  });
});

describe("payers", () => {
  it("needs a name and a payer ID of 2 to 15 letters, digits or hyphens", () => {
    expect(validatePayer({ ...payerDraftFrom(null), name: " " })).toEqual({ name: "Enter the payer name" });
    expect(validatePayer({ ...payerDraftFrom(null), name: "Aetna", payer_id: "0" })).toEqual({
      payer_id: "Use 2 to 15 letters, digits or hyphens",
    });
    expect(validatePayer({ ...payerDraftFrom(null), name: "Aetna", payer_id: "60054" })).toEqual({});
  });

  it("sends the payer ID in capitals, or nothing when it is blank", () => {
    const blue = { name: " Blue Cross Blue Shield of Texas ", payer_id: "g84980", plan_type: "commercial" as const, active: true };
    expect(payerInputFrom(blue)).toEqual({ name: "Blue Cross Blue Shield of Texas", payer_id: "G84980", plan_type: "commercial", active: true });
    expect(payerInputFrom({ ...blue, payer_id: "  " }).payer_id).toBeNull();
  });
});

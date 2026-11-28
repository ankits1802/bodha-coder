import { describe, expect, it } from "vitest";
import type { FilePreview, Provider } from "@/lib/api/types";
import { applyPreview, newEntry, placed, type References, type UploadEntry } from "../uploadEntries";
import { MIXED_PAYER, batchPayerOptions, chosenPayer, payerOptions, sharedPayer, usualPayer } from "../uploadPayers";

const MEDICARE = { id: "payer-medicare", name: "Medicare Part B", plan_type: "medicare" } as const;
const AETNA = { id: "payer-aetna", name: "Aetna", plan_type: "commercial" } as const;

function provider(id: string, payer: string | null): Provider {
  return { id, name: id, credential: "MD", place_code: "11", payer, active: true } as Provider;
}

const REFERENCES: References = {
  providers: [provider("prov-medicare", MEDICARE.id), provider("prov-aetna", AETNA.id), provider("prov-retired", "payer-gone"), provider("prov-none", null)],
  places: [{ code: "11", name: "Office" }],
  payers: [MEDICARE, AETNA],
};

function file(id: string): UploadEntry {
  return newEntry(new File(["%PDF-1.7"], `${id}.pdf`, { type: "application/pdf" }), id);
}

function preview(change: Partial<FilePreview>): FilePreview {
  return {
    file_name: "a.pdf",
    cpt: null,
    duplicate: false,
    provider_id: "prov-medicare",
    service_date: "2026-11-24",
    place_code: "11",
    patient_name: null,
    confidence: { provider: 0.99, service_date: 0.95, place: 0.95, patient: 0 },
    overall: 0.95,
    check: false,
    payer_id: null,
    payer_confidence: 0,
    payer_confident: false,
    ...change,
  };
}

function read(change: Partial<FilePreview>, entry: UploadEntry = file("1")): UploadEntry {
  const [first] = applyPreview([entry], [entry.id], [preview(change)], REFERENCES);
  return first as UploadEntry;
}

describe("the payer from page one", () => {
  it("is applied when page one names it clearly", () => {
    expect(read({ payer_id: AETNA.id, payer_confidence: 0.9, payer_confident: true })).toMatchObject({
      payerId: AETNA.id,
      payerSource: "document",
      suggestedPayer: null,
    });
  });

  it("is only suggested below the threshold, and the provider's usual payer fills the field", () => {
    expect(read({ payer_id: AETNA.id, payer_confidence: 0.6 })).toMatchObject({
      payerId: MEDICARE.id,
      payerSource: "provider",
      suggestedPayer: AETNA.id,
    });
  });

  it("leaves the payer empty with no usual payer and no clear page one", () => {
    expect(read({ provider_id: "prov-none" })).toMatchObject({ payerId: "", payerSource: null, suggestedPayer: null });
  });

  it("never replaces a payer the person chose", () => {
    const chosen = chosenPayer(file("1"), "");
    expect(read({ payer_id: AETNA.id, payer_confidence: 0.9, payer_confident: true }, chosen)).toMatchObject({ payerId: "", payerSource: "person" });
  });
});

describe("the provider's usual payer", () => {
  it("counts only while it is an active payer of the practice", () => {
    expect(usualPayer("prov-medicare", REFERENCES)).toBe(MEDICARE.id);
    expect(usualPayer("prov-retired", REFERENCES)).toBeNull();
    expect(usualPayer("prov-none", REFERENCES)).toBeNull();
  });

  it("follows a change of provider but leaves a payer from page one or from the person alone", () => {
    const fromProvider = read({});
    expect(placed(fromProvider, { providerId: "prov-aetna" }, REFERENCES)).toMatchObject({ payerId: AETNA.id, payerSource: "provider" });
    expect(placed(fromProvider, { providerId: "prov-none" }, REFERENCES)).toMatchObject({ payerId: "", payerSource: null });
    const fromPage = read({ payer_id: AETNA.id, payer_confidence: 0.9, payer_confident: true });
    expect(placed(fromPage, { providerId: "prov-medicare" }, REFERENCES).payerId).toBe(AETNA.id);
    const fromPerson = chosenPayer(fromProvider, AETNA.id);
    expect(placed(fromPerson, { providerId: "prov-medicare" }, REFERENCES).payerId).toBe(AETNA.id);
  });
});

describe("payer options", () => {
  it("start with None and put a suggestion in its own group", () => {
    expect(payerOptions([MEDICARE, AETNA]).map((option) => option.label)).toEqual(["None", "Medicare Part B", "Aetna"]);
    expect(payerOptions([MEDICARE, AETNA], AETNA.id).map((option) => [option.label, option.group])).toEqual([
      ["None", undefined],
      ["Aetna", "Suggested"],
      ["Medicare Part B", "All payers"],
    ]);
  });

  it("show Several for the batch while files differ", () => {
    const one = chosenPayer(file("1"), MEDICARE.id);
    const two = chosenPayer(file("2"), AETNA.id);
    expect(sharedPayer([one, chosenPayer(file("3"), MEDICARE.id)])).toBe(MEDICARE.id);
    expect(sharedPayer([file("1"), file("2")])).toBe("");
    expect(sharedPayer([one, two])).toBeNull();
    expect(batchPayerOptions([MEDICARE], null)[0]).toEqual({ value: MIXED_PAYER, label: "Several", disabled: true });
    expect(batchPayerOptions([MEDICARE], "")[0]).toEqual({ value: "", label: "None" });
  });
});

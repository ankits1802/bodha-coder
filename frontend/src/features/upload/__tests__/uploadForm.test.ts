import { describe, expect, it } from "vitest";
import type { FilePreview, Provider } from "@/lib/api/types";
import {
  applyPreview,
  canStartUpload,
  entryStatus,
  makeUploadForm,
  newEntry,
  placed,
  sharedValue,
  withDuplicates,
  type References,
  type UploadEntry,
} from "../uploadEntries";

function pdf(name: string, body = "%PDF-1.7 note"): File {
  return new File([body], name, { type: "application/pdf" });
}

const PLACED = { providerId: "prov-1", serviceDate: "2026-11-25", placeCode: "11" };

function entry(file: File, id: string, change: Partial<UploadEntry> = {}): UploadEntry {
  return { ...newEntry(file, id), ...PLACED, ...change };
}

function provider(id: string, placeCode: string | null, payer: string | null = null): Provider {
  return {
    id,
    name: `Provider ${id}`,
    credential: "MD",
    specialty: null,
    npi: null,
    place_code: placeCode,
    payer,
    email: null,
    phone: null,
    channel: "email",
    active: true,
    details: {},
  } as Provider;
}

const REFERENCES: References = {
  providers: [provider("prov-1", "11", "payer-medicare"), provider("prov-2", "31", "payer-retired"), provider("prov-3", "99")],
  places: [
    { code: "11", name: "Office" },
    { code: "31", name: "Skilled nursing facility" },
  ],
  payers: [
    { id: "payer-medicare", name: "Medicare Part B", plan_type: "medicare" },
    { id: "payer-aetna", name: "Aetna", plan_type: "commercial" },
  ],
};

function preview(change: Partial<FilePreview>): FilePreview {
  return {
    file_name: "a.pdf",
    cpt: null,
    duplicate: false,
    provider_id: null,
    service_date: null,
    place_code: null,
    patient_name: null,
    confidence: { provider: 0, service_date: 0, place: 0, patient: 0 },
    overall: 0,
    check: true,
    payer_id: null,
    payer_confidence: 0,
    payer_confident: false,
    ...change,
  };
}

describe("makeUploadForm", () => {
  it("sends the default visit type and one detail per file with its own provider, date and place, in file order", () => {
    const entries = [
      entry(pdf("2026-11-25 - REYES MARISOL - 99215.pdf"), "1", { billed: " 99215, I10 ", payerId: "payer-medicare" }),
      entry(pdf("scan_0042.pdf", "%PDF other"), "2", { providerId: "prov-2", serviceDate: "2026-11-24", placeCode: "31" }),
      entry(pdf("2026-11-25 - OKONKWO DAVID - 99204.pdf", "%PDF third"), "3", { billed: "99204", visitType: "New patient" }),
    ];
    const form = makeUploadForm("Established patient", entries);
    expect(form.get("visit_type")).toBe("Established patient");
    expect(form.get("provider_id")).toBeNull();
    expect(JSON.parse(String(form.get("details")))).toEqual([
      { billed: "99215, I10", visit_type: null, provider_id: "prov-1", service_date: "2026-11-25", place_code: "11", payer: "payer-medicare" },
      { billed: null, visit_type: null, provider_id: "prov-2", service_date: "2026-11-24", place_code: "31", payer: null },
      { billed: "99204", visit_type: "New patient", provider_id: "prov-1", service_date: "2026-11-25", place_code: "11", payer: null },
    ]);
    expect((form.getAll("files") as File[]).map((file) => file.name)).toEqual([
      "2026-11-25 - REYES MARISOL - 99215.pdf",
      "scan_0042.pdf",
      "2026-11-25 - OKONKWO DAVID - 99204.pdf",
    ]);
  });

  it("keeps the date of service as the calendar date chosen, with no time zone shift", () => {
    const form = makeUploadForm("Established patient", [entry(pdf("a.pdf"), "1", { serviceDate: "2026-12-31" })]);
    const details = JSON.parse(String(form.get("details"))) as { service_date: string }[];
    expect(details.map((detail) => detail.service_date)).toEqual(["2026-12-31"]);
  });

  it("leaves out duplicates the user did not keep and files already uploaded, keeping details aligned with files", () => {
    const kept = withDuplicates([entry(pdf("chen.pdf"), "1", { billed: "99214" }), entry(pdf("chen.pdf"), "2", { billed: "99214" })]);
    const form = makeUploadForm("Established patient", [...kept, entry(pdf("old.pdf", "%PDF old"), "3", { serverDuplicate: true })]);
    expect((form.getAll("files") as File[]).map((file) => file.name)).toEqual(["chen.pdf"]);
    expect(JSON.parse(String(form.get("details")))).toHaveLength(1);

    const keepBoth = kept.map((item) => (item.id === "2" ? { ...item, keep: true } : item));
    expect((makeUploadForm("Established patient", keepBoth).getAll("files") as File[]).length).toBe(2);
  });
});

describe("applyPreview", () => {
  it("fills provider, date, place, patient and codes from page 1 and marks a low-confidence file to check", () => {
    const rows = [newEntry(pdf("a.pdf"), "1"), newEntry(pdf("b.pdf", "%PDF b"), "2")];
    const read = applyPreview(rows, ["1", "2"], [
      preview({ provider_id: "prov-2", service_date: "2026-11-24", place_code: "31", patient_name: "Ruth Abernathy", cpt: "99309", overall: 0.95, check: false }),
      preview({ provider_id: "prov-1", service_date: null, place_code: "11", overall: 0, check: true, duplicate: true }),
    ], REFERENCES);
    expect(read[0]).toMatchObject({ providerId: "prov-2", serviceDate: "2026-11-24", placeCode: "31", patientName: "Ruth Abernathy", billed: "99309", check: false });
    expect(read[1]).toMatchObject({ providerId: "prov-1", serviceDate: "", check: true, serverDuplicate: true });
    expect(read.map(entryStatus)).toEqual(["ready", "uploaded"]);
    expect(read.map((row) => entryStatus({ ...row, serverDuplicate: false }))).toEqual(["ready", "check"]);
  });

  it("never overwrites what the user already chose", () => {
    const chosen = newEntry(pdf("a.pdf"), "1");
    const edited = { ...chosen, providerId: "prov-3", billed: "99213" };
    const [read] = applyPreview([edited], ["1"], [preview({ provider_id: "prov-1", cpt: "99215", service_date: "2026-11-20" })], REFERENCES);
    expect(read).toMatchObject({ providerId: "prov-3", billed: "99213", serviceDate: "2026-11-20" });
  });
});

describe("per-file placement", () => {
  it("takes the place from the chosen provider when it is an active place, and clears Check", () => {
    const row = entry(pdf("a.pdf"), "1", { placeCode: "11", check: true });
    expect(placed(row, { providerId: "prov-2" }, REFERENCES)).toMatchObject({ providerId: "prov-2", placeCode: "31", check: false });
    expect(placed(row, { providerId: "prov-3" }, REFERENCES)).toMatchObject({ providerId: "prov-3", placeCode: "11" });
    expect(placed(row, { providerId: "prov-2", placeCode: "11" }, REFERENCES).placeCode).toBe("11");
  });

  it("shows the shared value of all files, or nothing when they differ", () => {
    const rows = [entry(pdf("a.pdf"), "1"), entry(pdf("b.pdf", "%PDF b"), "2", { placeCode: "31" })];
    expect(sharedValue(rows, "providerId")).toBe("prov-1");
    expect(sharedValue(rows, "placeCode")).toBe("");
  });
});

describe("canStartUpload", () => {
  it("refuses while a file has no provider, date or place, or a billed code is invalid", () => {
    const valid = [entry(pdf("a.pdf"), "1", { billed: "99213" })];
    expect(canStartUpload(valid)).toBe(true);
    expect(canStartUpload([...valid, entry(pdf("b.pdf", "%PDF b"), "2", { providerId: "" })])).toBe(false);
    expect(canStartUpload([entry(pdf("a.pdf"), "1", { serviceDate: "2026-02-30" })])).toBe(false);
    expect(canStartUpload([entry(pdf("a.pdf"), "1", { placeCode: "" })])).toBe(false);
    expect(canStartUpload([entry(pdf("a.pdf"), "1", { billed: "9921" })])).toBe(false);
    expect(canStartUpload([entry(pdf("a.pdf"), "1", { check: true })])).toBe(true);
  });
});

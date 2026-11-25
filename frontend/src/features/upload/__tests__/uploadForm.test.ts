import { describe, expect, it } from "vitest";
import type { UploadPlan } from "@/lib/api/types";
import { canStartUpload, makeUploadForm, newEntry, withDuplicates, type UploadEntry } from "../uploadEntries";

function pdf(name: string, body = "%PDF-1.7 note"): File {
  return new File([body], name, { type: "application/pdf" });
}

const PLAN: UploadPlan = {
  provider_id: "prov-1",
  service_date: "2026-11-25",
  place_code: "11",
  visit_type: "Established patient",
};

function entry(file: File, id: string, change: Partial<UploadEntry> = {}): UploadEntry {
  return { ...newEntry(file, id), ...change };
}

describe("makeUploadForm", () => {
  it("sends the plan fields exactly as entered", () => {
    const form = makeUploadForm(PLAN, [entry(pdf("a.pdf"), "1", { billed: "99215, I10" })]);
    expect(form.get("provider_id")).toBe("prov-1");
    expect(form.get("service_date")).toBe("2026-11-25");
    expect(form.get("place_code")).toBe("11");
    expect(form.get("visit_type")).toBe("Established patient");
  });

  it("keeps the date of service as the calendar date from the date input, with no time zone shift", () => {
    const lateEvening = { ...PLAN, service_date: "2026-12-31" };
    const form = makeUploadForm(lateEvening, [entry(pdf("a.pdf"), "1")]);
    expect(form.get("service_date")).toBe("2026-12-31");
    expect(String(form.get("service_date"))).not.toContain("T");
  });

  it("sends one detail per file, in the same order as the files", () => {
    const entries = [
      entry(pdf("2026-11-25 - REYES MARISOL - 99215.pdf"), "1", { billed: " 99215, I10 " }),
      entry(pdf("scan_0042.pdf", "%PDF other"), "2"),
      entry(pdf("2026-11-25 - OKONKWO DAVID - 99204.pdf", "%PDF third"), "3", { billed: "99204", visitType: "New patient" }),
    ];
    const form = makeUploadForm(PLAN, entries);
    expect(JSON.parse(String(form.get("details")))).toEqual([
      { billed: "99215, I10", visit_type: null },
      { billed: null, visit_type: null },
      { billed: "99204", visit_type: "New patient" },
    ]);
    const files = form.getAll("files") as File[];
    expect(files.map((file) => file.name)).toEqual([
      "2026-11-25 - REYES MARISOL - 99215.pdf",
      "scan_0042.pdf",
      "2026-11-25 - OKONKWO DAVID - 99204.pdf",
    ]);
  });

  it("leaves out duplicates the user did not keep, keeping details aligned with files", () => {
    const first = pdf("chen.pdf");
    const copy = pdf("chen.pdf");
    const kept = withDuplicates([entry(first, "1", { billed: "99214" }), entry(copy, "2", { billed: "99214" })]);
    const form = makeUploadForm(PLAN, kept);
    expect((form.getAll("files") as File[]).length).toBe(1);
    expect(JSON.parse(String(form.get("details")))).toEqual([{ billed: "99214", visit_type: null }]);

    const keepBoth = kept.map((item) => (item.id === "2" ? { ...item, keep: true } : item));
    const both = makeUploadForm(PLAN, keepBoth);
    expect((both.getAll("files") as File[]).length).toBe(2);
    expect(JSON.parse(String(both.get("details")))).toHaveLength(2);
  });
});

describe("canStartUpload", () => {
  it("refuses while a billed code is invalid or the date is not a calendar date", () => {
    const valid = [entry(pdf("a.pdf"), "1", { billed: "99213" })];
    expect(canStartUpload(PLAN, valid)).toBe(true);
    expect(canStartUpload(PLAN, [entry(pdf("a.pdf"), "1", { billed: "9921" })])).toBe(false);
    expect(canStartUpload({ ...PLAN, service_date: "2026-02-30" }, valid)).toBe(false);
    expect(canStartUpload({ ...PLAN, provider_id: "" }, valid)).toBe(false);
  });
});

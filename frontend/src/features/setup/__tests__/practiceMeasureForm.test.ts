import { describe, expect, it } from "vitest";
import { codesFrom, draftFrom, inputFrom, validateDraft, type MeasureDraft } from "../practiceMeasureForm";

const DRAFT: MeasureDraft = {
  name: "Diabetic foot follow-up",
  identifier: "QM-7",
  in_scope: "Adults with diabetes seen in the office.",
  out_of_scope: "",
  to_meet: "A monofilament foot exam result and the follow-up interval.",
  met_codes: "g2178",
  not_met_codes: "",
};

describe("practice measure form", () => {
  it("accepts a complete measure and sends trimmed text, upper-case codes and no empty optional fields", () => {
    expect(validateDraft(DRAFT)).toEqual({});
    expect(inputFrom({ ...DRAFT, name: "  Diabetic foot follow-up ", identifier: " " })).toEqual({
      name: "Diabetic foot follow-up",
      identifier: null,
      in_scope: "Adults with diabetes seen in the office.",
      out_of_scope: null,
      to_meet: "A monofilament foot exam result and the follow-up interval.",
      met_codes: ["G2178"],
      not_met_codes: [],
    });
  });

  it("reads codes separated by commas, spaces or semicolons once each", () => {
    expect(codesFrom("3046f, G8427;g8427  1090F-8P")).toEqual(["3046F", "G8427", "1090F-8P"]);
    expect(codesFrom(" ")).toEqual([]);
  });

  it.each([
    ["117", "Add letters, for example QM-117"],
    ["MIPS #226", "Add letters, for example QM-117"],
    ["p004", "Add letters, for example QM-117"],
    ["QM;7", "Use up to 20 letters, digits, spaces, periods, slashes, hyphens or underscores"],
  ])("refuses the identifier %s", (identifier, message) => {
    expect(validateDraft({ ...DRAFT, identifier })).toEqual({ identifier: message });
  });

  it("refuses short or missing text and codes that are not reporting codes", () => {
    expect(validateDraft({ ...DRAFT, name: "QM", in_scope: "Adults", to_meet: "" })).toEqual({
      name: "Use 3 to 80 characters",
      in_scope: "Use 10 to 600 characters",
      to_meet: "Use 10 to 1,000 characters",
    });
    expect(validateDraft({ ...DRAFT, met_codes: "E11.9" })).toEqual({ met_codes: "Use up to 4 codes such as 3046F, G8427 or 1090F-8P" });
    expect(validateDraft({ ...DRAFT, met_codes: "G8427 G8428 G8429 G8430 G8431" })).toEqual({
      met_codes: "Use up to 4 codes such as 3046F, G8427 or 1090F-8P",
    });
    expect(validateDraft({ ...DRAFT, not_met_codes: "G2178" })).toEqual({ not_met_codes: "A code can report only one outcome" });
  });

  it("starts an edit from the saved measure", () => {
    const draft = draftFrom({
      key: "P001",
      version: 2,
      name: "Diabetic foot follow-up",
      identifier: null,
      in_scope: "Adults with diabetes seen in the office.",
      out_of_scope: null,
      to_meet: "A foot exam.",
      met_codes: ["G2178", "G2179"],
      not_met_codes: [],
      changed_at: "2026-11-28T10:00:00Z",
    });
    expect(draft).toMatchObject({ identifier: "", out_of_scope: "", met_codes: "G2178, G2179", not_met_codes: "" });
  });
});

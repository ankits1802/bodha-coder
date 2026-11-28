import { describe, expect, it } from "vitest";
import type { PracticeSetup, SetupSection } from "@/lib/api/types";
import { touchedErrors } from "../providerForm";
import { fieldError, isNavKey, nextIncomplete } from "../setupModel";

function section(complete: boolean): SetupSection {
  return { fields: [], optional: [], values: {}, complete };
}

const SETUP = {
  sections: {
    practice_details: section(false),
    providers: section(true),
    payers: section(false),
    payments: section(true),
    coding_rules: section(false),
  },
  missing_npi: 0,
} as unknown as PracticeSetup;

describe("setup flow", () => {
  it("goes on from a finished section to the next one still incomplete, skipping finished ones", () => {
    const detailsDone = { ...SETUP, sections: { ...SETUP.sections, practice_details: section(true) } } as PracticeSetup;
    expect(nextIncomplete(detailsDone, "practice_details")).toBe("payers");
    const payersDone = { ...SETUP, sections: { ...SETUP.sections, payers: section(true) } } as PracticeSetup;
    expect(nextIncomplete(payersDone, "payers")).toBe("coding_rules");
  });

  it("stays on a section the save left incomplete, such as payers without a payer", () => {
    expect(nextIncomplete(SETUP, "payers")).toBeNull();
    expect(nextIncomplete(SETUP, "practice_details")).toBeNull();
  });

  it("never moves away from the sections that are not scored", () => {
    expect(nextIncomplete(SETUP, "checks")).toBeNull();
    expect(nextIncomplete(SETUP, "intake")).toBeNull();
    expect(nextIncomplete(SETUP, "mips")).toBeNull();
  });

  it("checks the group NPI and tax ID shapes and leaves empty or free text fields alone", () => {
    expect(fieldError("group_npi", "123456789")).toBe("Enter the 10-digit NPI");
    expect(fieldError("group_npi", "1234567893")).toBeNull();
    expect(fieldError("tax_id", "12-345678")).toBe("Enter the 9-digit EIN, like 12-3456789");
    expect(fieldError("tax_id", "12-3456789")).toBeNull();
    expect(fieldError("tax_id", "123456789")).toBeNull();
    expect(fieldError("tax_id", "")).toBeNull();
    expect(fieldError("address", "x")).toBeNull();
  });

  it("checks the ZIP+4, state, phone and taxonomy code a claim needs", () => {
    expect(fieldError("zip", "62701")).toBeNull();
    expect(fieldError("zip", "62701-1234")).toBeNull();
    expect(fieldError("zip", "627011234")).toBeNull();
    expect(fieldError("zip", "6270")).toBe("Enter a 5 or 9-digit ZIP code");
    expect(fieldError("state", "il")).toBeNull();
    expect(fieldError("state", "Illinois")).toBe("Use the 2-letter state code");
    expect(fieldError("phone", "(555) 555-1234")).toBeNull();
    expect(fieldError("phone", "555-1234")).toBe("Enter a 10-digit phone number");
    expect(fieldError("taxonomy_code", "207q00000x")).toBeNull();
    expect(fieldError("taxonomy_code", "207Q00000")).toBe("Use the 10-character taxonomy code ending in X");
  });

  it("lists the clearinghouse among the sections that are not scored", () => {
    expect(isNavKey("clearinghouse")).toBe(true);
    expect(nextIncomplete(SETUP, "clearinghouse")).toBeNull();
  });

  it("shows a provider field error only once the field was left", () => {
    expect(touchedErrors({ npi: "Enter a 10-digit NPI", email: "Enter an email" }, ["npi"])).toEqual({ npi: "Enter a 10-digit NPI" });
    expect(touchedErrors({ npi: "Enter a 10-digit NPI" }, [])).toEqual({});
  });
});

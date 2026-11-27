import { describe, expect, it } from "vitest";
import type { PracticeSetup, SetupSection } from "@/lib/api/types";
import { touchedErrors } from "../providerForm";
import { fieldError, nextIncomplete } from "../setupModel";

function section(complete: boolean): SetupSection {
  return { fields: [], values: {}, complete };
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
  it("goes on to the next section still incomplete, skipping finished ones", () => {
    expect(nextIncomplete(SETUP, "practice_details")).toBe("payers");
    expect(nextIncomplete(SETUP, "payers")).toBe("coding_rules");
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

  it("shows a provider field error only once the field was left", () => {
    expect(touchedErrors({ npi: "Enter a 10-digit NPI", email: "Enter an email" }, ["npi"])).toEqual({ npi: "Enter a 10-digit NPI" });
    expect(touchedErrors({ npi: "Enter a 10-digit NPI" }, [])).toEqual({});
  });
});

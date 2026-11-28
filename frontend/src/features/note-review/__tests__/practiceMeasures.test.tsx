import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MipsSection } from "../components/MipsSection";
import { practiceMark, practiceReportCodes } from "../practiceMeasures";
import { finding } from "./fixtures";

const CODES = {
  collectionType: "Practice measure",
  specifications: [],
  codes: [
    { code: "G2178", role: "met", meaning: "Reported when the measure is met", criterion: null, source: "practice" },
    { code: "G2179", role: "not-met", meaning: "Reported when the measure is not met", criterion: null, source: "practice" },
  ],
  note: null,
};

const practice = finding({
  kind: "mips",
  key: "mips:PRACTICE #P001",
  action: "info",
  title: "Diabetic foot follow-up",
  reasoning: "Adult with diabetes seen in the office.",
  code_before: null,
  detail: { status: "missing", reportingCodes: CODES, practiceMeasure: { key: "P001", version: 3, identifier: "QM-7" } },
});
const cms = finding({
  kind: "mips",
  key: "mips:MIPS #117",
  action: "info",
  title: "Diabetes: Eye Exam",
  reasoning: "Adult with diabetes.",
  code_before: null,
  detail: { status: "met", reportingCodes: { ...CODES, collectionType: "MIPS CQM" }, practiceMeasure: null },
});

describe("practice measures in the review", () => {
  it("reads the practice mark and the codes for the measure's outcome", () => {
    expect(practiceMark(practice)).toEqual({ key: "P001", version: 3, identifier: "QM-7" });
    expect(practiceMark(cms)).toBeNull();
    expect(practiceReportCodes(practice, "missing")).toEqual(["G2179"]);
    expect(practiceReportCodes(practice, "met")).toEqual(["G2178"]);
    expect(practiceReportCodes(practice, "not_applicable")).toEqual([]);
  });

  it("marks a practice measure apart from a CMS measure and names its code", () => {
    render(<MipsSection measures={[cms, practice]} />);

    expect(screen.getByText("Practice measure · QM-7")).toBeInTheDocument();
    expect(screen.getByText("Report G2179")).toBeInTheDocument();
    expect(screen.getAllByText(/^Practice measure/)).toHaveLength(1);
    expect(screen.queryByText("Report G2178")).not.toBeInTheDocument();
  });
});

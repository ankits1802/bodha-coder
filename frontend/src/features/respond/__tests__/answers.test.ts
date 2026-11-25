import { describe, expect, it } from "vitest";
import type { AddendumQuestion } from "@/lib/api/types";
import { canSign, previewLines, toAnswers, type Drafts } from "../answers";

const stage: AddendumQuestion = {
  key: "cdiq-1",
  text: "What stage is the chronic kidney disease?",
  context: ["CKD, stable"],
  options: ["Stage 3a", "Stage 3b", "Other"],
};

const cause: AddendumQuestion = {
  key: "cdiq-2",
  text: "Is the kidney disease due to the diabetes?",
  context: [],
  options: ["Yes", "No", "Clinically undetermined", "Other"],
};

const questions = [stage, cause];

describe("addendum preview", () => {
  it("writes one line per answered question in question order", () => {
    const drafts: Drafts = {
      "cdiq-2": { choice: "Yes", comment: "" },
      "cdiq-1": { choice: "Stage 3b", comment: "" },
    };
    expect(previewLines(questions, drafts)).toEqual([
      "What stage is the chronic kidney disease? Stage 3b.",
      "Is the kidney disease due to the diabetes? Yes.",
    ]);
  });

  it("appends a trimmed comment after a listed choice", () => {
    const drafts: Drafts = { "cdiq-2": { choice: "Yes", comment: "  Diabetic nephropathy on biopsy  " } };
    expect(previewLines(questions, drafts)).toEqual([
      "Is the kidney disease due to the diabetes? Yes. Diabetic nephropathy on biopsy",
    ]);
  });

  it("uses the comment as the reply when Other is chosen", () => {
    const drafts: Drafts = { "cdiq-1": { choice: "Other", comment: "Stage 4, eGFR trending down" } };
    expect(previewLines(questions, drafts)).toEqual(["What stage is the chronic kidney disease? Stage 4, eGFR trending down."]);
  });

  it("leaves out Other without a comment and unanswered questions", () => {
    const drafts: Drafts = { "cdiq-1": { choice: "Other", comment: "   " } };
    expect(previewLines(questions, drafts)).toEqual([]);
  });
});

describe("signing", () => {
  const answered: Drafts = {
    "cdiq-1": { choice: "Stage 3a", comment: "" },
    "cdiq-2": { choice: "No", comment: "" },
  };

  it("needs the confirmation", () => {
    expect(canSign(questions, answered, false)).toBe(false);
    expect(canSign(questions, answered, true)).toBe(true);
  });

  it("needs every question answered", () => {
    expect(canSign(questions, { "cdiq-1": { choice: "Stage 3a", comment: "" } }, true)).toBe(false);
  });

  it("needs a comment when Other is chosen", () => {
    const other: Drafts = { ...answered, "cdiq-1": { choice: "Other", comment: "" } };
    expect(canSign(questions, other, true)).toBe(false);
    expect(canSign(questions, { ...other, "cdiq-1": { choice: "Other", comment: "Stage 4" } }, true)).toBe(true);
  });

  it("sends trimmed comments and null when there is none", () => {
    const drafts: Drafts = {
      "cdiq-1": { choice: "Other", comment: " Stage 4 " },
      "cdiq-2": { choice: "No", comment: "" },
    };
    expect(toAnswers(questions, drafts)).toEqual([
      { key: "cdiq-1", choice: "Other", comment: "Stage 4" },
      { key: "cdiq-2", choice: "No", comment: null },
    ]);
  });
});

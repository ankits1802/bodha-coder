import type { StatusTone } from "@/components/ui/StatusDot";

export type CodeKind = "procedure" | "diagnosis";

export interface ClaimCodes {
  procedures: readonly string[];
  diagnoses: readonly string[];
}

export interface SampleStatus {
  label: string;
  tone: StatusTone;
}

export interface SampleFinding {
  key: string;
  kind: CodeKind;
  before: string | null;
  after: string;
  title: string;
  status: SampleStatus;
  reasoning: string;
  evidence: readonly string[];
}

export interface SampleNote {
  key: string;
  tab: string;
  visit: string;
  header: string;
  note: string;
  verdict: SampleStatus;
  billed: ClaimCodes;
  findings: readonly SampleFinding[];
}

const TOO_HIGH: SampleStatus = { label: "Billed too high", tone: "bad" };
const TOO_LOW: SampleStatus = { label: "Billed too low", tone: "low" };
const SPECIFIC: SampleStatus = { label: "More specific", tone: "ok" };

export const SAMPLE_NOTES: readonly SampleNote[] = [
  {
    key: "sinus",
    tab: "Billed too high",
    visit: "Sinus infection",
    header: "Sample note · Established patient",
    note: "34-year-old with 10 days of facial pressure and nasal congestion, worse over the last 3 days after starting to improve. Afebrile. Tender over the left maxillary sinus. Lungs clear.\n\nAssessment: Acute maxillary sinusitis.\n\nPlan: Amoxicillin-clavulanate 875 mg twice daily for 7 days. Saline rinses. Return if not better in a week.",
    verdict: { label: "Billed one level too high", tone: "bad" },
    billed: { procedures: ["99214"], diagnoses: ["J01.90"] },
    findings: [
      {
        key: "em",
        kind: "procedure",
        before: "99214",
        after: "99213",
        title: "Office visit, established, low MDM",
        status: TOO_HIGH,
        reasoning: "One acute, uncomplicated illness and no data reviewed. The prescription is moderate risk, but 99214 needs two of three MDM elements at moderate.",
        evidence: ["10 days of facial pressure and nasal congestion", "Afebrile", "Amoxicillin-clavulanate 875 mg twice daily for 7 days"],
      },
      {
        key: "sinus-site",
        kind: "diagnosis",
        before: "J01.90",
        after: "J01.00",
        title: "Acute maxillary sinusitis, unspecified",
        status: SPECIFIC,
        reasoning: "The note names the maxillary sinus.",
        evidence: ["Acute maxillary sinusitis"],
      },
    ],
  },
  {
    key: "follow-up",
    tab: "Billed too low",
    visit: "Diabetes follow-up",
    header: "Sample note · Established patient · Medicare",
    note: "72-year-old followed here for primary care since 2019, seen for diabetes and hypertension.\n\nType 2 diabetes: A1c 7.1, stable on metformin. Hypertension: 126/78, at goal on lisinopril. Reviewed BMP: creatinine 0.9, potassium 4.3.\n\nPlan: Continue metformin 1000 mg twice daily and lisinopril 20 mg daily, refills sent. Return in 3 months to keep managing both conditions.",
    verdict: { label: "Billed one level too low", tone: "low" },
    billed: { procedures: ["99213"], diagnoses: ["E11.9", "I10", "Z79.84"] },
    findings: [
      {
        key: "em",
        kind: "procedure",
        before: "99213",
        after: "99214",
        title: "Office visit, established, moderate MDM",
        status: TOO_LOW,
        reasoning: "Two stable chronic illnesses with prescription drug management meet moderate MDM.",
        evidence: [
          "A1c 7.1, stable on metformin",
          "126/78, at goal on lisinopril",
          "Continue metformin 1000 mg twice daily and lisinopril 20 mg daily, refills sent",
        ],
      },
      {
        key: "longitudinal",
        kind: "procedure",
        before: null,
        after: "G2211",
        title: "Visit complexity add-on, longitudinal care",
        status: { label: "Missed add-on", tone: "low" },
        reasoning: "Medicare add-on for ongoing care: this practice is the continuing focal point for the patient's health care.",
        evidence: ["followed here for primary care since 2019", "Return in 3 months to keep managing both conditions"],
      },
    ],
  },
  {
    key: "kidney",
    tab: "HCC capture",
    visit: "Diabetes with CKD",
    header: "Sample note · Established patient · Medicare Advantage",
    note: "67-year-old with type 2 diabetes and hypertension, here to review labs.\n\neGFR 52, stable for over a year. Urine albumin-to-creatinine ratio 48. BP 128/76.\n\nAssessment: Type 2 diabetes with diabetic chronic kidney disease, stage 3a. Hypertension, controlled.\n\nPlan: Continue metformin and lisinopril. Start empagliflozin 10 mg daily. Recheck eGFR and potassium in 3 months.",
    verdict: { label: "Diagnoses less specific than the note", tone: "warn" },
    billed: { procedures: ["99214"], diagnoses: ["E11.9", "N18.9", "I10", "Z79.84"] },
    findings: [
      {
        key: "diabetes",
        kind: "diagnosis",
        before: "E11.9",
        after: "E11.22",
        title: "Type 2 diabetes with diabetic chronic kidney disease",
        status: SPECIFIC,
        reasoning: "Diabetes with chronic kidney disease takes the combination code, with the stage coded beside it.",
        evidence: ["Type 2 diabetes with diabetic chronic kidney disease"],
      },
      {
        key: "stage",
        kind: "diagnosis",
        before: "N18.9",
        after: "N18.31",
        title: "Chronic kidney disease, stage 3a",
        status: { label: "HCC 329", tone: "ok" },
        reasoning: "The stage is documented. N18.31 maps to HCC 329 in CMS-HCC V28; N18.9 maps to none.",
        evidence: ["stage 3a", "eGFR 52, stable for over a year"],
      },
      {
        key: "hypertension",
        kind: "diagnosis",
        before: "I10",
        after: "I12.9",
        title: "Hypertensive chronic kidney disease, stage 1 to 4",
        status: { label: "Combination code", tone: "ok" },
        reasoning: "ICD-10-CM presumes hypertension and chronic kidney disease are linked.",
        evidence: ["Hypertension, controlled"],
      },
    ],
  },
];

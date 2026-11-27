import type { CheckKey } from "@/lib/api/types";

export const CHECK_TEXT = {
  labels: {
    em: "Visit level (E/M)",
    icd: "Diagnoses (ICD-10)",
    cdi: "Questions for providers",
    audit: "Audit risk",
    mips: "Quality measures (MIPS)",
    hcc: "Risk adjustment (HCC)",
  } satisfies Record<CheckKey, string>,
} as const;

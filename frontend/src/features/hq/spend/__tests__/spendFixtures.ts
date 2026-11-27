import type { HqExpenditure, PracticeSpend, ProviderSpend, SpendFigures } from "@/lib/api/types";

function figures(
  analyses: number,
  notes: number,
  inputTokens: number,
  outputTokens: number,
  cost: number,
  perNote: number | null,
  unpriced: number,
): SpendFigures {
  return {
    analyses,
    notes,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    cost_usd: cost,
    cost_per_note_usd: perNote,
    unpriced_analyses: unpriced,
  };
}

const VARGA: ProviderSpend = { id: "v-varga", name: "Elena Varga", ...figures(3, 1, 1_220_000, 150_000, 1.06, 1.06, 0) };
const HADDAD: ProviderSpend = { id: "v-haddad", name: "Omar Haddad", ...figures(2, 2, 130_000, 16_000, 0.08, null, 1) };
const RUIZ: ProviderSpend = { id: "v-ruiz", name: "Ana Ruiz", ...figures(1, 1, 2_000_000, 0, 1, 1, 0) };

const LAKESIDE: PracticeSpend = {
  id: "p-lakeside",
  name: "Lakeside",
  plan: "professional",
  plan_monthly_cents: 24_900,
  ...figures(5, 3, 1_350_000, 166_000, 1.14, null, 1),
  providers: [VARGA, HADDAD],
};

const HILLSIDE: PracticeSpend = {
  id: "p-hillside",
  name: "Hillside, PC",
  plan: "essentials",
  plan_monthly_cents: 14_900,
  ...figures(1, 1, 2_000_000, 0, 1, 1, 0),
  providers: [RUIZ],
};

export const NOVEMBER_SPEND: HqExpenditure = {
  from: "2026-11-01",
  to: "2026-11-28",
  time_zone: "UTC",
  totals: figures(6, 4, 3_350_000, 166_000, 2.14, null, 1),
  practices: [LAKESIDE, HILLSIDE],
  unpriced_models: ["gemini-unlisted"],
};

const QUIET: PracticeSpend = {
  id: "p-quiet",
  name: "Quiet Creek",
  plan: "trial",
  plan_monthly_cents: null,
  ...figures(0, 0, 0, 0, 0, null, 0),
  providers: [],
};

export const WITH_QUIET_PRACTICE: HqExpenditure = { ...NOVEMBER_SPEND, practices: [LAKESIDE, HILLSIDE, QUIET] };

export const NO_SPEND: HqExpenditure = {
  ...NOVEMBER_SPEND,
  totals: figures(0, 0, 0, 0, 0, null, 0),
  practices: [],
  unpriced_models: [],
};

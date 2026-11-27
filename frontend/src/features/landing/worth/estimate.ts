export interface AmountBounds {
  min: number;
  max: number;
  step: number;
}

export const WORTH_BOUNDS = {
  visits: { min: 0, max: 10000, step: 50 },
  lowPercent: { min: 0, max: 30, step: 0.5 },
  highPercent: { min: 0, max: 30, step: 0.5 },
  difference: { min: 0, max: 300, step: 1 },
} as const satisfies Record<string, AmountBounds>;

export type WorthField = keyof typeof WORTH_BOUNDS;
export type WorthInputs = Record<WorthField, number>;
export type WorthDrafts = Record<WorthField, string>;

export const WORTH_FIELDS: readonly WorthField[] = ["visits", "lowPercent", "highPercent", "difference"];

export const WORTH_DEFAULTS: WorthInputs = { visits: 1000, lowPercent: 5, highPercent: 3, difference: 40 };

export interface Worth {
  recovered: number;
  exposure: number;
  recoveredYear: number;
  exposureYear: number;
}

const MONTHS_A_YEAR = 12;
const PERCENT = 100;

export function levelDollars(visits: number, percent: number, difference: number): number {
  return visits * (percent / PERCENT) * difference;
}

export function estimateWorth(inputs: WorthInputs): Worth {
  const recovered = levelDollars(inputs.visits, inputs.lowPercent, inputs.difference);
  const exposure = levelDollars(inputs.visits, inputs.highPercent, inputs.difference);
  return { recovered, exposure, recoveredYear: recovered * MONTHS_A_YEAR, exposureYear: exposure * MONTHS_A_YEAR };
}

export function readAmount(text: string, bounds: AmountBounds): number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value) || value < bounds.min || value > bounds.max) return null;
  return value;
}

export function readDrafts(drafts: WorthDrafts): WorthInputs | null {
  const values: Partial<WorthInputs> = {};
  for (const field of WORTH_FIELDS) {
    const value = readAmount(drafts[field], WORTH_BOUNDS[field]);
    if (value === null) return null;
    values[field] = value;
  }
  return values as WorthInputs;
}

export function draftsOf(inputs: WorthInputs): WorthDrafts {
  return {
    visits: String(inputs.visits),
    lowPercent: String(inputs.lowPercent),
    highPercent: String(inputs.highPercent),
    difference: String(inputs.difference),
  };
}

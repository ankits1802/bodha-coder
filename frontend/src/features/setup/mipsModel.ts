import { ApiError } from "@/lib/api/errors";
import { saveMips } from "@/lib/api/practice";
import type { MipsOverview } from "@/lib/api/types";

export type MipsMode = "standard" | "custom";
export type MipsSaveResult = "saved" | "conflict";

const CONFLICT = 409;

export function initialMode(overview: MipsOverview): MipsMode {
  return overview.uses_standard ? "standard" : "custom";
}

export function initialChoice(overview: MipsOverview): Set<string> {
  const ids = overview.uses_standard ? overview.standard.map((measure) => measure.id) : overview.measure_ids;
  return new Set(ids);
}

export function chosenIds(overview: MipsOverview, chosen: Set<string>): string[] {
  const order = [...overview.standard, ...overview.addable].map((measure) => measure.id);
  return order.filter((id, index) => chosen.has(id) && order.indexOf(id) === index);
}

export async function saveMeasureList(measureIds: string[], expected: string[]): Promise<MipsSaveResult> {
  try {
    await saveMips(measureIds, expected);
    return "saved";
  } catch (error) {
    if (error instanceof ApiError && error.status === CONFLICT) return "conflict";
    throw error;
  }
}

import { backendUrl } from "@/lib/backend";
import { PLAN_CATALOG_PATH } from "./plan";
import type { PlanCatalog } from "./types";

export const PLAN_CATALOG_REVALIDATE_SECONDS = 3600;
export const PLAN_CATALOG_TIMEOUT_MS = 3000;

export async function loadPlanCatalog(): Promise<PlanCatalog | null> {
  try {
    const response = await fetch(`${backendUrl()}${PLAN_CATALOG_PATH}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: PLAN_CATALOG_REVALIDATE_SECONDS },
      signal: AbortSignal.timeout(PLAN_CATALOG_TIMEOUT_MS),
    });
    return response.ok ? ((await response.json()) as PlanCatalog) : null;
  } catch {
    return null;
  }
}

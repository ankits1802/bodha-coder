"use client";

import { getPlanCatalog } from "@/lib/api/plan";
import type { PlanCatalog } from "@/lib/api/types";
import { LOOKUP_SECONDS } from "./remoteCache";
import { useRemote, type Remote } from "./useRemote";

export const PLAN_CATALOG_KEY = "plan-catalog";

export function usePlanCatalog(): Remote<PlanCatalog> {
  return useRemote(PLAN_CATALOG_KEY, getPlanCatalog, LOOKUP_SECONDS);
}

"use client";

import { getPlanStatus } from "@/lib/api/plan";
import type { PlanStatus } from "@/lib/api/types";
import { useRemote, type Remote } from "./useRemote";

export const PLAN_STATUS_KEY = "plan-status";
const PLAN_STATUS_SECONDS = 60;

export function usePlanStatus(enabled = true): Remote<PlanStatus> {
  return useRemote(enabled ? PLAN_STATUS_KEY : null, getPlanStatus, PLAN_STATUS_SECONDS);
}

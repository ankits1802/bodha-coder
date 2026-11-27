"use client";

import { getSetup } from "@/lib/api/practice";
import type { PracticeSetup } from "@/lib/api/types";
import { useRemote, type Remote } from "./useRemote";

export const PRACTICE_SETUP_KEY = "practice-setup";

export function usePracticeSetup(enabled = true): Remote<PracticeSetup> {
  return useRemote(enabled ? PRACTICE_SETUP_KEY : null, getSetup);
}

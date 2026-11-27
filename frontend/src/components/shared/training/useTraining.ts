"use client";

import { useRemote, type Remote } from "@/hooks/useRemote";
import { getTraining } from "@/lib/api/quality";
import type { TrainingOverview } from "@/lib/api/types";

export const TRAINING_KEY = "training";

export function useTraining(enabled = true): Remote<TrainingOverview> {
  return useRemote(enabled ? TRAINING_KEY : null, getTraining);
}

import { addDays } from "@/lib/dates";
import type { TrainingInput } from "@/lib/api/types";

export interface TrainingDraft {
  traineeId: string;
  providerId: string;
  start: string;
  end: string;
  size: string;
}

const PERIOD_DAYS = 90;
const DEFAULT_SIZE = "10";
const MAX_SIZE = 100;
const SIZE_PATTERN = /^\d{1,3}$/;

export function firstTrainingDraft(today: string): TrainingDraft {
  return { traineeId: "", providerId: "", start: addDays(today, 1 - PERIOD_DAYS) ?? today, end: today, size: DEFAULT_SIZE };
}

export function trainingInput(draft: TrainingDraft): TrainingInput | null {
  const size = SIZE_PATTERN.test(draft.size) ? Number(draft.size) : 0;
  if (!draft.traineeId || !draft.start || !draft.end || draft.start > draft.end || size < 1 || size > MAX_SIZE) {
    return null;
  }
  return {
    trainee_id: draft.traineeId,
    start: draft.start,
    end: draft.end,
    size,
    provider_id: draft.providerId || null,
  };
}

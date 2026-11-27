import { addDays } from "@/lib/dates";
import type { QualityOptions, SampleInput, SampleScope } from "@/lib/api/types";

export interface SampleDraft {
  scope: SampleScope;
  providerId: string;
  specialty: string;
  start: string;
  end: string;
  size: string;
  reviewerIds: string[];
}

export const SCOPES: readonly SampleScope[] = ["practice", "provider", "specialty"];
const PERIOD_DAYS = 30;
const SIZE_PATTERN = /^\d{1,3}$/;

export function firstDraft(today: string): SampleDraft {
  return {
    scope: "practice",
    providerId: "",
    specialty: "",
    start: addDays(today, 1 - PERIOD_DAYS) ?? today,
    end: today,
    size: "",
    reviewerIds: [],
  };
}

export function defaultSize(draft: SampleDraft, options: QualityOptions): number {
  return draft.scope === "specialty" ? options.specialty_size : options.default_size;
}

export function toggled(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
}

export function sampleInput(draft: SampleDraft): SampleInput | null {
  const sizeOk = draft.size === "" || SIZE_PATTERN.test(draft.size);
  const scopeOk =
    draft.scope === "practice" || (draft.scope === "provider" ? draft.providerId !== "" : draft.specialty !== "");
  if (!sizeOk || !scopeOk || draft.reviewerIds.length === 0 || !draft.start || !draft.end || draft.start > draft.end) {
    return null;
  }
  return {
    scope: draft.scope,
    start: draft.start,
    end: draft.end,
    reviewer_ids: draft.reviewerIds,
    size: draft.size === "" ? null : Number(draft.size),
    provider_id: draft.scope === "provider" ? draft.providerId : null,
    specialty: draft.scope === "specialty" ? draft.specialty : null,
  };
}

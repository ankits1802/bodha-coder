"use client";

import { useRemote, type Remote } from "@/hooks/useRemote";
import { useSettled } from "@/hooks/useSettled";
import { searchHq } from "@/lib/api/hq";
import type { HqSearchResults } from "@/lib/api/types";
import { MIN_HQ_SEARCH_LENGTH } from "./hqSearchModel";

export interface HqSearch {
  ready: boolean;
  remote: Remote<HqSearchResults>;
}

export function useHqSearch(text: string): HqSearch {
  const term = useSettled(text.trim());
  const ready = term.length >= MIN_HQ_SEARCH_LENGTH && text.trim().length >= MIN_HQ_SEARCH_LENGTH;
  const remote = useRemote(ready ? `hq-search:${term}` : null, () => searchHq(term));
  return { ready, remote };
}

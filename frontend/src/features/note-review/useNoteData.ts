"use client";

import { useRemote } from "@/hooks/useRemote";
import { getNote } from "@/lib/api/notes";
import type { Lane } from "@/lib/api/types";
import { getQueue } from "@/lib/api/work";
import { LANE_ORDER } from "@/lib/labels";

export interface Neighbours {
  previous: string | null;
  next: string | null;
  index: number | null;
  total: number;
}

const NO_NEIGHBOURS: Neighbours = { previous: null, next: null, index: null, total: 0 };

export function parseLane(value: string | null): Lane | null {
  return LANE_ORDER.find((lane) => lane === value) ?? null;
}

export function useNote(noteId: string) {
  return useRemote(`note:${noteId}`, () => getNote(noteId));
}

export function useNeighbours(noteId: string, lane: Lane | null): Neighbours {
  const remote = useRemote(`neighbours:${lane ?? "all"}`, () => getQueue(lane ? { lane } : {}));
  if (remote.state.status !== "success") return NO_NEIGHBOURS;
  const page = remote.state.data;
  const ids = page.items.map((item) => item.id);
  const total = lane ? Math.max(page.lanes[lane].total, ids.length) : ids.length;
  const at = ids.indexOf(noteId);
  if (at < 0) return { previous: null, next: ids.find((id) => id !== noteId) ?? null, index: null, total };
  return { previous: ids[at - 1] ?? null, next: ids[at + 1] ?? null, index: at + 1, total };
}

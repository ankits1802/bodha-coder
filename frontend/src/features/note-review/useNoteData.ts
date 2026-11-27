"use client";

import { forgetNoteDetail } from "@/components/shared/noteDetail";
import { editRemote, forgetRemote, loadRemote } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import type { Lane, QueuePage } from "@/lib/api/types";
import { getQueue } from "@/lib/api/work";
import { LANE_ORDER } from "@/lib/labels";

export interface Neighbours {
  previous: string | null;
  next: string | null;
  index: number | null;
  total: number;
}

const NO_NEIGHBOURS: Neighbours = { previous: null, next: null, index: null, total: 0 };
const ORDER_SECONDS = 120;

const orderKey = (lane: Lane | null): string => `neighbours:${lane ?? "all"}`;

export function parseLane(value: string | null): Lane | null {
  return LANE_ORDER.find((lane) => lane === value) ?? null;
}

export function neighboursIn(page: QueuePage, noteId: string, lane: Lane | null): Neighbours {
  const ids = page.items.map((item) => item.id);
  const total = lane ? Math.max(page.lanes[lane].total, ids.length) : ids.length;
  const at = ids.indexOf(noteId);
  if (at < 0) return { previous: null, next: ids.find((id) => id !== noteId) ?? null, index: null, total };
  return { previous: ids[at - 1] ?? null, next: ids[at + 1] ?? null, index: at + 1, total };
}

export function withoutNote(page: QueuePage, noteId: string, lane: Lane | null): QueuePage {
  if (!page.items.some((item) => item.id === noteId)) return page;
  const items = page.items.filter((item) => item.id !== noteId);
  if (!lane) return { ...page, items };
  const count = page.lanes[lane];
  return { ...page, items, lanes: { ...page.lanes, [lane]: { ...count, total: Math.max(0, count.total - 1) } } };
}

function loadOrder(lane: Lane | null): Promise<QueuePage> {
  return getQueue(lane ? { lane } : {});
}

export function reviewOrder(lane: Lane | null): Promise<QueuePage> {
  return loadRemote(orderKey(lane), () => loadOrder(lane), ORDER_SECONDS);
}

export function useNeighbours(noteId: string, lane: Lane | null): Neighbours {
  const remote = useRemote(orderKey(lane), () => loadOrder(lane), ORDER_SECONDS);
  return remote.state.status === "success" ? neighboursIn(remote.state.data, noteId, lane) : NO_NEIGHBOURS;
}

export function leaveReviewOrder(noteId: string, lane: Lane | null): void {
  editRemote<QueuePage>(orderKey(lane), (page) => withoutNote(page, noteId, lane));
  forgetNoteDetail(noteId);
}

export function forgetReviewOrder(lane: Lane | null): void {
  forgetRemote(orderKey(lane));
}

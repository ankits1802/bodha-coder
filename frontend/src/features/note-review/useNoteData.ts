"use client";

import { forgetNoteDetail } from "@/components/shared/noteDetail";
import { editRemote, forgetRemote, loadRemote } from "@/hooks/remoteCache";
import { useRemote } from "@/hooks/useRemote";
import type { Lane, LaneReason, ProviderReason, QueuePage } from "@/lib/api/types";
import { getQueue } from "@/lib/api/work";
import { isLane, isLaneReason } from "@/lib/labels";

export interface Neighbours {
  previous: string | null;
  next: string | null;
  index: number | null;
  total: number;
}

export interface ReviewScope {
  lane: Lane | null;
  reason: LaneReason | null;
}

const NO_NEIGHBOURS: Neighbours = { previous: null, next: null, index: null, total: 0 };
const ORDER_SECONDS = 120;

const orderKey = (scope: ReviewScope): string => `neighbours:${scope.lane ?? "all"}:${scope.reason ?? "any"}`;

export function parseScope(lane: string | null, reason: string | null): ReviewScope {
  return { lane: isLane(lane) ? lane : null, reason: isLaneReason(reason) ? reason : null };
}

export function isScoped(scope: ReviewScope): boolean {
  return scope.lane !== null || scope.reason !== null;
}

export function neighboursIn(page: QueuePage, noteId: string, scope: ReviewScope): Neighbours {
  const ids = page.items.map((item) => item.id);
  const total = isScoped(scope) ? Math.max(page.total, ids.length) : ids.length;
  const at = ids.indexOf(noteId);
  if (at < 0) return { previous: null, next: ids.find((id) => id !== noteId) ?? null, index: null, total };
  return { previous: ids[at - 1] ?? null, next: ids[at + 1] ?? null, index: at + 1, total };
}

function isProviderReason(reason: LaneReason | null, page: QueuePage): reason is ProviderReason {
  return reason !== null && Object.hasOwn(page.provider_reasons, reason);
}

function fewer<C extends { total: number }>(count: C): C {
  return { ...count, total: Math.max(0, count.total - 1) };
}

export function withoutNote(page: QueuePage, noteId: string, scope: ReviewScope): QueuePage {
  if (!page.items.some((item) => item.id === noteId)) return page;
  const items = page.items.filter((item) => item.id !== noteId);
  const { lane, reason } = scope;
  const lanes = lane ? { ...page.lanes, [lane]: fewer(page.lanes[lane]) } : page.lanes;
  const reasons = isProviderReason(reason, page) ? { ...page.provider_reasons, [reason]: fewer(page.provider_reasons[reason]) } : page.provider_reasons;
  return { ...page, items, total: Math.max(0, page.total - 1), lanes, provider_reasons: reasons };
}

function loadOrder(scope: ReviewScope): Promise<QueuePage> {
  return getQueue({ lane: scope.lane ?? undefined, reason: scope.reason ?? undefined });
}

export function reviewOrder(scope: ReviewScope): Promise<QueuePage> {
  return loadRemote(orderKey(scope), () => loadOrder(scope), ORDER_SECONDS);
}

export function useNeighbours(noteId: string, scope: ReviewScope): Neighbours {
  const remote = useRemote(orderKey(scope), () => loadOrder(scope), ORDER_SECONDS);
  return remote.state.status === "success" ? neighboursIn(remote.state.data, noteId, scope) : NO_NEIGHBOURS;
}

export function leaveReviewOrder(noteId: string, scope: ReviewScope): void {
  editRemote<QueuePage>(orderKey(scope), (page) => withoutNote(page, noteId, scope));
  forgetNoteDetail(noteId);
}

export function forgetReviewOrder(scope: ReviewScope): void {
  forgetRemote(orderKey(scope));
}

"use client";

import { useRouter } from "next/navigation";
import { showToast } from "@/components/shared/toast/toastStore";
import { urlFor } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { reopenNote } from "@/lib/api/notes";
import { getToday } from "@/lib/api/work";
import { COMPLIANCE_PATH, notePath } from "@/lib/paths";
import { useSession } from "@/lib/session/useSession";
import { nextLaneView } from "./nextLane";
import { REVIEW_TEXT } from "./strings";
import {
  forgetReviewOrder,
  leaveReviewOrder,
  neighboursIn,
  reviewOrder,
  useNeighbours,
  type Neighbours,
  type ReviewScope,
} from "./useNoteData";

export interface ReviewNavigation {
  neighbours: Neighbours;
  backHref: string;
  go: (noteId: string) => void;
  moveOn: () => void;
  approved: (patient: string | null) => void;
  complianceDone: (message: string) => void;
}

export function useReviewNavigation(noteId: string, scope: ReviewScope): ReviewNavigation {
  const router = useRouter();
  const { user } = useSession();
  const neighbours = useNeighbours(noteId, scope);
  const query = { lane: scope.lane, reason: scope.reason };
  const backHref = urlFor("/queue", query);
  const go = (target: string) => router.push(urlFor(notePath(target), query));

  async function nextNote(): Promise<string | null> {
    if (neighbours.next !== null || neighbours.index !== null) return neighbours.next;
    const page = await reviewOrder(scope).catch(() => null);
    return page ? neighboursIn(page, noteId, scope).next : null;
  }

  async function nextLaneHref(): Promise<string> {
    const totals = await getToday().catch(() => null);
    const view = totals ? nextLaneView(totals, scope, user?.role) : null;
    return view ? urlFor("/queue", { lane: view.lane, reason: view.reason }) : backHref;
  }

  function goOn(next: string | null): void {
    if (next) go(next);
    else void nextLaneHref().then((href) => router.push(href));
  }

  function undo(): void {
    reopenNote(noteId).then(
      () => {
        forgetReviewOrder(scope);
        go(noteId);
      },
      (error: unknown) => showToast(messageOf(error)),
    );
  }

  function approved(patient: string | null): void {
    showToast(REVIEW_TEXT.approvedToast(patient ?? REVIEW_TEXT.patientUnknown), { label: REVIEW_TEXT.undo, run: undo });
    void nextNote().then((next) => {
      leaveReviewOrder(noteId, scope);
      goOn(next);
    });
  }

  function complianceDone(message: string): void {
    leaveReviewOrder(noteId, scope);
    showToast(message);
    router.push(COMPLIANCE_PATH);
  }

  return { neighbours, backHref, go, moveOn: () => void nextNote().then(goOn), approved, complianceDone };
}

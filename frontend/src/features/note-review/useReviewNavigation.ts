"use client";

import { useRouter } from "next/navigation";
import { showToast } from "@/components/shared/toast/toastStore";
import { urlFor } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { reopenNote } from "@/lib/api/notes";
import type { Lane } from "@/lib/api/types";
import { REVIEW_TEXT } from "./strings";
import { forgetReviewOrder, leaveReviewOrder, neighboursIn, reviewOrder, useNeighbours, type Neighbours } from "./useNoteData";

export interface ReviewNavigation {
  neighbours: Neighbours;
  backHref: string;
  go: (noteId: string) => void;
  moveOn: () => void;
  approved: (patient: string | null) => void;
}

export function useReviewNavigation(noteId: string, lane: Lane | null): ReviewNavigation {
  const router = useRouter();
  const neighbours = useNeighbours(noteId, lane);
  const backHref = urlFor("/queue", { lane });
  const go = (target: string) => router.push(urlFor(`/notes/${encodeURIComponent(target)}`, { lane }));

  async function nextNote(): Promise<string | null> {
    if (neighbours.next !== null || neighbours.index !== null) return neighbours.next;
    const page = await reviewOrder(lane).catch(() => null);
    return page ? neighboursIn(page, noteId, lane).next : null;
  }

  function goOn(next: string | null): void {
    if (next) go(next);
    else router.push(backHref);
  }

  function undo(): void {
    reopenNote(noteId).then(
      () => {
        forgetReviewOrder(lane);
        go(noteId);
      },
      (error: unknown) => showToast(messageOf(error)),
    );
  }

  function approved(patient: string | null): void {
    showToast(REVIEW_TEXT.approvedToast(patient ?? REVIEW_TEXT.patientUnknown), { label: REVIEW_TEXT.undo, run: undo });
    void nextNote().then((next) => {
      leaveReviewOrder(noteId, lane);
      goOn(next);
    });
  }

  return { neighbours, backHref, go, moveOn: () => void nextNote().then(goOn), approved };
}

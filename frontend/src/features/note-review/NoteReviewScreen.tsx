"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { RemoteView } from "@/components/ui/RemoteView";
import { placeName, usePlaceNames } from "@/hooks/usePlaceNames";
import { urlFor } from "@/lib/api/client";
import type { Lane } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { ReviewTopBar } from "./components/ReviewTopBar";
import { ReviewWorkspace } from "./components/ReviewWorkspace";
import { reviewPermissions } from "./permissions";
import { canReplacePdf } from "./replacePdf";
import { REVIEW_TEXT } from "./strings";
import { parseLane, useNeighbours, useNote } from "./useNoteData";
import { useReviewActions } from "./useReviewActions";

const REMOTE_TEXT = { loading: REVIEW_TEXT.loading, empty: REVIEW_TEXT.notFound, retry: REVIEW_TEXT.retry };

function NoteReview({ noteId, lane }: { noteId: string; lane: Lane | null }) {
  const { user } = useSession();
  const router = useRouter();
  const note = useNote(noteId);
  const neighbours = useNeighbours(noteId, lane);
  const backHref = urlFor("/queue", { lane });
  const go = (target: string) => router.push(urlFor(`/notes/${encodeURIComponent(target)}`, { lane }));
  const approved = () => (neighbours.next ? go(neighbours.next) : router.push(backHref));
  const actions = useReviewActions(noteId, { approved, changed: note.reload });
  const detail = note.state.status === "success" ? note.state.data : null;
  const placeNames = usePlaceNames();
  const code = detail?.note.place_code ?? null;
  const name = placeName(placeNames, code);
  const placeLabel = code && name && name !== code ? REVIEW_TEXT.placeNamed(name, code) : code;
  const title = detail
    ? [detail.note.provider.name, placeLabel, formatCalendarDay(detail.note.service_date)].filter(Boolean).join(" · ")
    : null;

  return (
    <div className="flex min-h-screen flex-col">
      <ReviewTopBar
        backHref={backHref}
        title={title}
        neighbours={neighbours}
        onGo={go}
        onOpenPdf={detail ? actions.openPdf : null}
        pdfPending={actions.pdfPending}
        replacePdf={detail && canReplacePdf(user?.role, detail.note.status) ? { noteId, onReplaced: note.reload } : null}
      />
      <main id="main" className="flex flex-1 flex-col">
        <RemoteView state={note.state} text={REMOTE_TEXT} onRetry={note.reload}>
          {(data) => (
            <ReviewWorkspace
              detail={data}
              placeLabel={placeLabel ?? ""}
              permissions={reviewPermissions(user?.role, data)}
              actions={actions}
              neighbours={neighbours}
              onGo={go}
              onReplace={note.replace}
              onReload={note.reload}
              onApproved={approved}
            />
          )}
        </RemoteView>
      </main>
    </div>
  );
}

export function NoteReviewScreen({ noteId }: { noteId: string }) {
  const searchParams = useSearchParams();
  const lane = parseLane(searchParams.get("lane"));
  return (
    <AreaGuard area="queue">
      <NoteReview key={noteId} noteId={noteId} lane={lane} />
    </AreaGuard>
  );
}

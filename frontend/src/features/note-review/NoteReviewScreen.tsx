"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { AreaGuard } from "@/components/shared/AreaGuard";
import { prefetchNoteDetail, useNoteDetail } from "@/components/shared/noteDetail";
import { RemoteView } from "@/components/ui/RemoteView";
import { placeName, usePlaceNames } from "@/hooks/usePlaceNames";
import { formatCalendarDay } from "@/lib/format";
import { useSession } from "@/lib/session/useSession";
import { NoteSkeleton } from "./components/NoteSkeleton";
import { ReviewTopBar } from "./components/ReviewTopBar";
import { ReviewWorkspace } from "./components/ReviewWorkspace";
import { reviewPermissions } from "./permissions";
import { canReplacePdf } from "./replacePdf";
import { REVIEW_TEXT } from "./strings";
import { parseScope, type ReviewScope } from "./useNoteData";
import { useReviewActions } from "./useReviewActions";
import { useReviewNavigation } from "./useReviewNavigation";

const REMOTE_TEXT = { loading: REVIEW_TEXT.loading, empty: REVIEW_TEXT.notFound, retry: REVIEW_TEXT.retry };

function NoteReview({ noteId, scope }: { noteId: string; scope: ReviewScope }) {
  const { user } = useSession();
  const note = useNoteDetail(noteId);
  const nav = useReviewNavigation(noteId, scope);
  const detail = note.state.status === "success" ? note.state.data : null;
  const actions = useReviewActions(noteId, {
    approved: () => nav.approved(detail?.note.patient_name ?? null),
    complianceDone: (decision) => nav.complianceDone(REVIEW_TEXT.complianceDone[decision]),
    changed: note.reload,
  });
  const placeNames = usePlaceNames();
  const code = detail?.note.place_code ?? null;
  const name = placeName(placeNames, code);
  const placeLabel = code && name && name !== code ? REVIEW_TEXT.placeNamed(name, code) : code;
  const title = detail
    ? [detail.note.provider.name, placeLabel, formatCalendarDay(detail.note.service_date)].filter(Boolean).join(" · ")
    : null;
  const next = nav.neighbours.next;
  const loaded = detail !== null;

  useEffect(() => {
    if (loaded && next) prefetchNoteDetail(next);
  }, [loaded, next]);

  return (
    <div className="flex min-h-screen flex-col">
      <ReviewTopBar
        backHref={nav.backHref}
        title={title}
        neighbours={nav.neighbours}
        onGo={nav.go}
        onOpenPdf={detail ? actions.openPdf : null}
        pdfPending={actions.pdfPending}
        replacePdf={detail && canReplacePdf(user?.role, detail.note.status) ? { noteId, onReplaced: note.reload } : null}
      />
      <main id="main" className="flex flex-1 flex-col">
        {note.state.status === "loading" ? (
          <NoteSkeleton label={REVIEW_TEXT.loading} />
        ) : (
          <RemoteView state={note.state} text={REMOTE_TEXT} onRetry={note.reload}>
            {(data) => (
              <ReviewWorkspace
                detail={data}
                placeLabel={placeLabel ?? ""}
                permissions={reviewPermissions(user?.role, data)}
                actions={actions}
                neighbours={nav.neighbours}
                onGo={nav.go}
                onReplace={note.replace}
                onReload={note.reload}
                onComplianceDone={nav.complianceDone}
              />
            )}
          </RemoteView>
        )}
      </main>
    </div>
  );
}

export function NoteReviewScreen({ noteId }: { noteId: string }) {
  const searchParams = useSearchParams();
  const scope = parseScope(searchParams.get("lane"), searchParams.get("reason"));
  return (
    <AreaGuard area="queue">
      <NoteReview key={noteId} noteId={noteId} scope={scope} />
    </AreaGuard>
  );
}

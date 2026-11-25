import type { Metadata } from "next";
import { Suspense } from "react";
import { NoteReviewScreen } from "@/features/note-review/NoteReviewScreen";
import { REVIEW_TEXT } from "@/features/note-review/strings";

export const metadata: Metadata = { title: REVIEW_TEXT.pageTitle };

export default async function NotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={null}>
      <NoteReviewScreen noteId={id} />
    </Suspense>
  );
}

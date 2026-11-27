"use client";

import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { Spinner } from "@/components/ui/Spinner";
import { useRemote } from "@/hooks/useRemote";
import { getNoteDay } from "@/lib/api/defensibility";
import { DayBannerView } from "./DayBannerView";
import { DAY_TEXT } from "./strings";

export function DayBanner({ noteId }: { noteId: string }) {
  const day = useRemote(`note-day:${noteId}`, () => getNoteDay(noteId));
  const { state } = day;
  if (state.status === "loading") {
    return (
      <div className="flex items-center gap-2 px-1 text-subhead text-secondary">
        <Spinner size="sm" label={DAY_TEXT.loading} />
      </div>
    );
  }
  if (state.status === "error") {
    const retry = (
      <Button size="sm" onClick={day.reload}>
        {DAY_TEXT.retry}
      </Button>
    );
    return (
      <InlineAlert tone="bad" action={retry}>
        {DAY_TEXT.failed}
      </InlineAlert>
    );
  }
  const lonely = state.data.notes.length <= 1 && state.data.flags.length === 0;
  return lonely ? null : <DayBannerView day={state.data} noteId={noteId} />;
}

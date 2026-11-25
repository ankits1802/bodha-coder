import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import type { NoteHeader } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";

interface StatusBannerProps {
  note: NoteHeader;
  onRetry: (() => void) | null;
  retryPending: boolean;
}

export function StatusBanner({ note, onRetry, retryPending }: StatusBannerProps) {
  const words = REVIEW_TEXT.banner;
  if (note.status === "queued" || note.status === "reading") return <InlineAlert tone="warn">{words.reading}</InlineAlert>;
  if (note.status === "approved" || note.status === "exported") {
    return <InlineAlert tone="ok">{note.status === "approved" ? words.approved : words.exported}</InlineAlert>;
  }
  if (note.status === "failed") {
    const action = onRetry ? (
      <Button size="sm" onClick={onRetry} pending={retryPending}>
        {words.retry}
      </Button>
    ) : null;
    return (
      <InlineAlert tone="bad" action={action}>
        {words.failed}
      </InlineAlert>
    );
  }
  if (note.flag_reason) return <InlineAlert tone="warn">{REVIEW_TEXT.flagged(note.flag_reason)}</InlineAlert>;
  return null;
}

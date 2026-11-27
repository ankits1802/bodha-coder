"use client";

import { useId, useState } from "react";
import { TextButton } from "@/components/ui/TextButton";
import { REVIEW_TEXT } from "../strings";
import { useComments } from "../useNoteComments";
import { CommentThread } from "./CommentThread";

const WORDS = REVIEW_TEXT.comments;

export function FindingThread({ findingKey, title }: { findingKey: string; title: string }) {
  const api = useComments();
  const panelId = useId();
  const [open, setOpen] = useState(false);
  if (!api) return null;
  const count = api.comments.filter((comment) => comment.finding_key === findingKey && !comment.removed).length;
  return (
    <div className="flex flex-col gap-2">
      <TextButton className="self-start text-footnote" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
        {WORDS.toggle(count)}
      </TextButton>
      {open ? (
        <div id={panelId}>
          <CommentThread api={api} findingKey={findingKey} label={WORDS.on(title)} />
        </div>
      ) : null}
    </div>
  );
}

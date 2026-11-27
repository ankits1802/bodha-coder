"use client";

import { Toggle } from "@/components/ui/Toggle";
import type { Finding } from "@/lib/api/types";
import { REVIEW_TEXT } from "../strings";
import { useComments } from "../useNoteComments";
import { CommentComposer, CommentList } from "./CommentThread";

const WORDS = REVIEW_TEXT.comments;

export function HistoryComments({ findings }: { findings: Finding[] }) {
  const api = useComments();
  if (!api) return null;
  const titles = new Map(findings.map((finding) => [finding.key, finding.title]));
  const groups = [...new Set(api.comments.map((comment) => comment.finding_key))];
  return (
    <div className="flex flex-col gap-4">
      {api.canSeeRemoved ? (
        <span className="flex items-center justify-between gap-3 text-subhead">
          {WORDS.showRemoved}
          <Toggle label={WORDS.showRemoved} checked={api.showRemoved} onChange={api.setShowRemoved} />
        </span>
      ) : null}
      {api.error ? (
        <p role="alert" className="m-0 text-footnote text-bad-text">
          {api.error}
        </p>
      ) : null}
      {groups.map((key) => (
        <section key={key ?? "note"} aria-label={key === null ? REVIEW_TEXT.history.noteThread : (titles.get(key) ?? key)} className="flex flex-col gap-2">
          <h4 className="m-0 text-footnote font-semibold text-secondary">
            {key === null ? REVIEW_TEXT.history.noteThread : (titles.get(key) ?? key)}
          </h4>
          <CommentList comments={api.comments.filter((comment) => comment.finding_key === key)} onRemove={(id) => void api.remove(id)} />
        </section>
      ))}
      <CommentComposer api={api} findingKey={null} label={WORDS.note} />
    </div>
  );
}

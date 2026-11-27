"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { TextButton } from "@/components/ui/TextButton";
import type { CommentPerson, NoteComment } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { mentionedIds } from "../mentions";
import { REVIEW_TEXT } from "../strings";
import type { NoteCommentsApi } from "../useNoteComments";
import { MentionInput } from "./MentionInput";

const WORDS = REVIEW_TEXT.comments;
export const COMMENT_MAX = 2000;

function CommentItem({ comment, onRemove }: { comment: NoteComment; onRemove: (id: string) => void }) {
  const removed = comment.removed;
  return (
    <li className="flex flex-col gap-1 border-t border-hairline py-2.5 first:border-t-0 first:pt-0">
      <span className="flex flex-wrap items-center gap-x-2 text-footnote text-secondary">
        <span className="font-medium text-label">{comment.author_name}</span>
        <span>{WORDS.role(comment.author_role)}</span>
        <time dateTime={comment.at}>{formatDateTime(comment.at)}</time>
        {comment.can_remove ? (
          <TextButton className="ml-auto" onClick={() => onRemove(comment.id)}>
            {WORDS.remove}
          </TextButton>
        ) : null}
      </span>
      <p className={`m-0 text-callout whitespace-pre-wrap ${removed ? "text-tertiary" : ""}`}>{comment.body}</p>
      {removed ? <span className="text-footnote text-tertiary">{WORDS.removedBy(removed.by, formatDateTime(removed.at))}</span> : null}
    </li>
  );
}

export function CommentList({ comments, onRemove }: { comments: NoteComment[]; onRemove: (id: string) => void }) {
  if (comments.length === 0) return null;
  return (
    <ul className="m-0 list-none p-0">
      {comments.map((comment) => (
        <CommentItem key={comment.id} comment={comment} onRemove={onRemove} />
      ))}
    </ul>
  );
}

export function CommentComposer({ api, findingKey, label }: { api: NoteCommentsApi; findingKey: string | null; label: string }) {
  const [text, setText] = useState("");
  const [chosen, setChosen] = useState<CommentPerson[]>([]);

  async function submit(): Promise<void> {
    const body = text.trim();
    if (body === "") return;
    if (await api.post(findingKey, body, mentionedIds(text, chosen))) {
      setText("");
      setChosen([]);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <MentionInput
        label={label}
        value={text}
        maxLength={COMMENT_MAX}
        people={api.people}
        onChange={setText}
        onMention={(person) => setChosen((current) => [...current, person])}
        onSubmit={() => void submit()}
      />
      {api.actionError ? (
        <p role="alert" className="m-0 text-footnote text-bad-text">
          {api.actionError}
        </p>
      ) : null}
      <div>
        <Button size="sm" pending={api.posting} disabled={text.trim() === ""} onClick={() => void submit()}>
          {WORDS.post}
        </Button>
      </div>
    </div>
  );
}

export function CommentThread({ api, findingKey, label }: { api: NoteCommentsApi; findingKey: string | null; label: string }) {
  const comments = api.comments.filter((comment) => comment.finding_key === findingKey);
  return (
    <div className="flex flex-col gap-3">
      <CommentList comments={comments} onRemove={(id) => void api.remove(id)} />
      <CommentComposer api={api} findingKey={findingKey} label={label} />
    </div>
  );
}

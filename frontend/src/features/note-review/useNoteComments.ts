"use client";

import { createContext, useContext, useState } from "react";
import { useAction } from "@/hooks/useAction";
import { useRemote } from "@/hooks/useRemote";
import { getCommentPeople, getComments, postComment, removeComment } from "@/lib/api/comments";
import type { CommentPerson, NoteComment, NoteComments } from "@/lib/api/types";

const PEOPLE_SECONDS = 300;

export interface NoteCommentsApi {
  comments: NoteComment[];
  people: CommentPerson[];
  error: string | null;
  canSeeRemoved: boolean;
  showRemoved: boolean;
  setShowRemoved: (value: boolean) => void;
  post: (findingKey: string | null, body: string, mentions: string[]) => Promise<boolean>;
  remove: (commentId: string) => Promise<void>;
  posting: boolean;
  actionError: string | null;
}

export const CommentsContext = createContext<NoteCommentsApi | null>(null);

export function useComments(): NoteCommentsApi | null {
  return useContext(CommentsContext);
}

function replaced(items: NoteComment[], updated: NoteComment, keepRemoved: boolean): NoteComment[] {
  if (!keepRemoved && updated.removed) return items.filter((item) => item.id !== updated.id);
  return items.map((item) => (item.id === updated.id ? updated : item));
}

export function useNoteComments(noteId: string, canSeeRemoved: boolean): NoteCommentsApi {
  const [showRemoved, setShowRemoved] = useState(false);
  const removed = canSeeRemoved && showRemoved;
  const remote = useRemote<NoteComments>(`comments:${noteId}:${removed}`, () => getComments(noteId, removed));
  const people = useRemote("comment-people", getCommentPeople, PEOPLE_SECONDS);
  const posting = useAction(postComment);
  const removing = useAction(removeComment);
  const items = remote.state.status === "success" ? remote.state.data.items : [];

  async function post(findingKey: string | null, body: string, mentions: string[]): Promise<boolean> {
    const outcome = await posting.run(noteId, { finding_key: findingKey, body, mentions });
    if (outcome.ok) remote.replace({ items: [...items, outcome.value] });
    return outcome.ok;
  }

  async function remove(commentId: string): Promise<void> {
    const outcome = await removing.run(commentId);
    if (outcome.ok) remote.replace({ items: replaced(items, outcome.value, removed) });
  }

  return {
    comments: items,
    people: people.state.status === "success" ? people.state.data : [],
    error: remote.state.status === "error" ? remote.state.error : null,
    canSeeRemoved,
    showRemoved: removed,
    setShowRemoved,
    post,
    remove,
    posting: posting.pending,
    actionError: posting.error ?? removing.error,
  };
}

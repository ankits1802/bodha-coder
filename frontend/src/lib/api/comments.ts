import { request } from "./client";
import type { CommentInput, CommentPerson, NoteComment, NoteComments } from "./types";

const commentsPath = (noteId: string): string => `/api/notes/${encodeURIComponent(noteId)}/comments`;

export function getComments(noteId: string, removed = false): Promise<NoteComments> {
  return request<NoteComments>(commentsPath(noteId), { query: { removed } });
}

export function postComment(noteId: string, comment: CommentInput): Promise<NoteComment> {
  return request<NoteComment>(commentsPath(noteId), { body: comment });
}

export function removeComment(commentId: string): Promise<NoteComment> {
  return request<NoteComment>(`/api/comments/${encodeURIComponent(commentId)}/remove`, { method: "POST" });
}

export function getCommentPeople(): Promise<CommentPerson[]> {
  return request<CommentPerson[]>("/api/comments/people");
}

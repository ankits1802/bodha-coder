import type { AddendumAnswer, AddendumQuestion } from "@/lib/api/types";

export const OTHER_ANSWER = "Other";

export interface AnswerDraft {
  choice: string | null;
  comment: string;
}

export type Drafts = Record<string, AnswerDraft>;

export const EMPTY_DRAFT: AnswerDraft = { choice: null, comment: "" };

export function draftFor(drafts: Drafts, key: string): AnswerDraft {
  return drafts[key] ?? EMPTY_DRAFT;
}

export function needsComment(draft: AnswerDraft): boolean {
  return draft.choice === OTHER_ANSWER && draft.comment.trim() === "";
}

export function isAnswered(draft: AnswerDraft): boolean {
  return draft.choice !== null && !needsComment(draft);
}

export function canSign(questions: AddendumQuestion[], drafts: Drafts, confirmed: boolean): boolean {
  return confirmed && questions.length > 0 && questions.every((question) => isAnswered(draftFor(drafts, question.key)));
}

export function addendumLine(question: AddendumQuestion, draft: AnswerDraft): string | null {
  if (!isAnswered(draft)) return null;
  const comment = draft.comment.trim();
  if (draft.choice === OTHER_ANSWER) return `${question.text} ${comment}.`;
  const extra = comment ? ` ${comment}` : "";
  return `${question.text} ${draft.choice}.${extra}`;
}

export function previewLines(questions: AddendumQuestion[], drafts: Drafts): string[] {
  return questions
    .map((question) => addendumLine(question, draftFor(drafts, question.key)))
    .filter((line): line is string => line !== null);
}

export function toAnswers(questions: AddendumQuestion[], drafts: Drafts): AddendumAnswer[] {
  return questions.map((question) => {
    const draft = draftFor(drafts, question.key);
    const comment = draft.comment.trim();
    return { key: question.key, choice: draft.choice ?? "", comment: comment || null };
  });
}

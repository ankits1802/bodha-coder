import type { AskBody, Channel, Finding } from "@/lib/api/types";
import { textValue } from "./findings";

export interface QuestionDraft {
  include: boolean;
  text: string;
}

export function initialDrafts(questions: Finding[]): Record<string, QuestionDraft> {
  return Object.fromEntries(
    questions.map((finding) => {
      const text = finding.kind === "diagnosis" ? (textValue(finding.reasoning) ?? finding.title) : finding.title;
      return [finding.key, { include: true, text }];
    }),
  );
}

export function askBody(questions: Finding[], drafts: Record<string, QuestionDraft>, channel: Channel, hold: boolean): AskBody {
  const chosen = questions.filter((finding) => drafts[finding.key]?.include);
  return {
    questions: chosen.map((finding) => ({ key: finding.key, text: drafts[finding.key]?.text.trim() ?? "" })),
    channel,
    hold,
  };
}

export function isAskValid(body: AskBody): boolean {
  return body.questions.length > 0 && body.questions.every((question) => question.text !== "");
}

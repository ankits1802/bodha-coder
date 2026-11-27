import type { CommentPerson } from "@/lib/api/types";

export interface ActiveMention {
  start: number;
  query: string;
}

export interface MentionEdit {
  text: string;
  caret: number;
}

const MENTION_LIMIT = 6;

export function activeMention(text: string, caret: number): ActiveMention | null {
  const before = text.slice(0, caret);
  const at = before.lastIndexOf("@");
  if (at < 0 || (at > 0 && !/\s/.test(before[at - 1] ?? ""))) return null;
  const query = before.slice(at + 1);
  if (query.includes("\n") || query.length > 40 || /\s\s/.test(query)) return null;
  return { start: at, query };
}

export function matchingPeople(people: CommentPerson[], query: string): CommentPerson[] {
  const wanted = query.trim().toLowerCase();
  return people.filter((person) => person.name.toLowerCase().includes(wanted)).slice(0, MENTION_LIMIT);
}

export function insertMention(text: string, mention: ActiveMention, caret: number, person: CommentPerson): MentionEdit {
  const inserted = `@${person.name} `;
  const next = text.slice(0, mention.start) + inserted + text.slice(caret);
  return { text: next, caret: mention.start + inserted.length };
}

export function mentionedIds(text: string, chosen: CommentPerson[]): string[] {
  const kept = chosen.filter((person) => text.includes(`@${person.name}`));
  return [...new Set(kept.map((person) => person.id))];
}

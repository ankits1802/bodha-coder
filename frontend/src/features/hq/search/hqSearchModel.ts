import type { HqSearchPerson, HqSearchResults } from "@/lib/api/types";
import { PRACTICE_STATUS_LABELS, ROLE_LABELS } from "@/lib/labels";
import { practiceHref } from "../practice/practiceTabs";
import { HQ_TEXT } from "../strings";

export const MIN_HQ_SEARCH_LENGTH = 2;

export type SearchGroup = "practices" | "people";

export interface SearchOption {
  key: string;
  group: SearchGroup;
  title: string;
  detail: string;
  href: string | null;
}

const words = HQ_TEXT.search;

function personDetail(person: HqSearchPerson): string {
  const memberships = person.practices.map((practice) => words.membership(practice.name, ROLE_LABELS[practice.role]));
  return [person.email, ...(memberships.length > 0 ? memberships : [words.noPractice])].join(" · ");
}

export function searchOptions(results: HqSearchResults): SearchOption[] {
  const practices = results.practices.map(
    (practice): SearchOption => ({
      key: `practice:${practice.id}`,
      group: "practices",
      title: practice.name,
      detail: PRACTICE_STATUS_LABELS[practice.status],
      href: practiceHref(practice.id),
    }),
  );
  const people = results.people.map((person): SearchOption => {
    const first = person.practices[0];
    return {
      key: `person:${person.id}`,
      group: "people",
      title: person.name,
      detail: personDetail(person),
      href: first ? practiceHref(first.id, "people") : null,
    };
  });
  return [...practices, ...people];
}

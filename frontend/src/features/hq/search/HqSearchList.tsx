import { optionId } from "@/hooks/useActiveOption";
import { HQ_TEXT } from "../strings";
import type { SearchGroup, SearchOption } from "./hqSearchModel";

const GROUPS: readonly SearchGroup[] = ["practices", "people"];
const words = HQ_TEXT.search;

interface HqSearchListProps {
  listId: string;
  options: SearchOption[];
  active: number;
  onActive: (index: number) => void;
  onOpen: (option: SearchOption) => void;
}

export function HqSearchList({ listId, options, active, onActive, onOpen }: HqSearchListProps) {
  const indexed = options.map((option, index) => ({ option, index }));
  const groups = GROUPS.map((group) => ({ group, entries: indexed.filter((entry) => entry.option.group === group) })).filter(
    (entry) => entry.entries.length > 0,
  );
  return (
    <div id={listId} role="listbox" aria-label={words.title} className="flex max-h-96 flex-col gap-3 overflow-y-auto">
      {groups.map(({ group, entries }) => (
        <div key={group} role="group" aria-labelledby={`${listId}-${group}`} className="flex flex-col gap-0.5">
          <span id={`${listId}-${group}`} className="px-3 pb-1 text-caption font-semibold text-secondary">
            {words[group]}
          </span>
          {entries.map(({ option, index }) => (
            <div
              key={option.key}
              id={optionId(listId, index)}
              role="option"
              aria-selected={index === active}
              aria-disabled={option.href === null ? true : undefined}
              onMouseMove={() => onActive(index)}
              onClick={() => onOpen(option)}
              className={`flex cursor-pointer flex-col gap-0.5 rounded-field px-3 py-2.5 ${index === active ? "bg-row-selected" : ""}`}
            >
              <span className="truncate text-body font-medium">{option.title}</span>
              <span className="truncate text-subhead text-secondary">{option.detail}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

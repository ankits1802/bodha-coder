import { noteStatus } from "@/components/shared/noteStatus";
import { StatusDot } from "@/components/ui/StatusDot";
import { optionId } from "@/hooks/useActiveOption";
import type { NoteSummary } from "@/lib/api/types";
import { formatCalendarDay } from "@/lib/format";
import { SEARCH_TEXT } from "./strings";

interface SearchResultListProps {
  listId: string;
  items: NoteSummary[];
  active: number;
  onActive: (index: number) => void;
  onOpen: (note: NoteSummary) => void;
}

export function SearchResultList({ listId, items, active, onActive, onOpen }: SearchResultListProps) {
  return (
    <ul id={listId} role="listbox" aria-label={SEARCH_TEXT.results} className="m-0 flex max-h-96 list-none flex-col gap-0.5 overflow-y-auto p-0">
      {items.map((item, index) => {
        const status = noteStatus(item);
        return (
          <li
            key={item.id}
            id={optionId(listId, index)}
            role="option"
            aria-selected={index === active}
            onMouseMove={() => onActive(index)}
            onClick={() => onOpen(item)}
            className={`flex cursor-pointer flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-field px-3 py-2.5 ${index === active ? "bg-row-selected" : ""}`}
          >
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="truncate text-body font-medium">{item.patient_name ?? item.file_name}</span>
              <span className="truncate text-subhead text-secondary">{SEARCH_TEXT.meta(item.provider_name, formatCalendarDay(item.service_date))}</span>
            </span>
            <StatusDot tone={status.tone}>{status.label}</StatusDot>
          </li>
        );
      })}
    </ul>
  );
}

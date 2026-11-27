import { FilterSelect } from "@/components/ui/FilterSelect";
import { SearchField } from "@/components/ui/SearchField";
import type { HqPractice } from "@/lib/api/types";
import { HQ_TEXT } from "../strings";
import { actionChoices, actionLabel } from "./activityModel";

interface ActivityFiltersProps {
  search: string;
  action: string | null;
  practiceId: string | null;
  actions: readonly string[];
  practices: HqPractice[];
  onSearch: (search: string) => void;
  onAction: (action: string) => void;
  onPractice: (practiceId: string) => void;
}

const words = HQ_TEXT.activity;

export function ActivityFilters({ search, action, practiceId, actions, practices, onSearch, onAction, onPractice }: ActivityFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <SearchField label={words.search} value={search} onChange={(event) => onSearch(event.target.value)} />
      <FilterSelect label={words.action} value={action ?? ""} onChange={(event) => onAction(event.target.value)}>
        <option value="">{words.anyAction}</option>
        {actionChoices(actions, action).map((choice) => (
          <option key={choice} value={choice}>
            {actionLabel(choice)}
          </option>
        ))}
      </FilterSelect>
      <FilterSelect label={words.practice} value={practiceId ?? ""} onChange={(event) => onPractice(event.target.value)}>
        <option value="">{words.anyPractice}</option>
        {practices.map((practice) => (
          <option key={practice.id} value={practice.id}>
            {practice.name}
          </option>
        ))}
      </FilterSelect>
    </div>
  );
}

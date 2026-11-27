import { SearchField } from "@/components/ui/SearchField";
import { Select } from "@/components/ui/Select";
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
      <Select
        variant="filter"
        label={words.action}
        value={action ?? ""}
        options={[{ value: "", label: words.anyAction }, ...actionChoices(actions, action).map((choice) => ({ value: choice, label: actionLabel(choice) }))]}
        onChange={onAction}
      />
      <Select
        variant="filter"
        label={words.practice}
        value={practiceId ?? ""}
        options={[{ value: "", label: words.anyPractice }, ...practices.map((practice) => ({ value: practice.id, label: practice.name }))]}
        onChange={onPractice}
      />
    </div>
  );
}

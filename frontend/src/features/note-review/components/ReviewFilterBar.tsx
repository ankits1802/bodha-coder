import { Button } from "@/components/ui/Button";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { REVIEW_FILTERS, type ReviewFilter } from "../reviewList";
import { REVIEW_TEXT } from "../strings";

interface ReviewFilterBarProps {
  filter: ReviewFilter;
  counts: Record<ReviewFilter, number>;
  onFilter: (filter: ReviewFilter) => void;
  onHistory: () => void;
}

export function ReviewFilterBar({ filter, counts, onFilter, onHistory }: ReviewFilterBarProps) {
  const segments = REVIEW_FILTERS.map((value) => ({ value, label: REVIEW_TEXT.filters[value], count: counts[value] }));
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-3.5">
      <SegmentedControl label={REVIEW_TEXT.filterLabel} value={filter} segments={segments} onChange={onFilter} size="sm" />
      <Button variant="plain" size="sm" onClick={onHistory}>
        {REVIEW_TEXT.historyOpen}
      </Button>
    </div>
  );
}

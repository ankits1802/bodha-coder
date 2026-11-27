import { CodeChange } from "@/components/ui/CodeChange";
import type { TrainingSuggestion } from "@/lib/api/types";
import { TRAINING_TEXT } from "../strings";

export function SuggestionList({ suggestions }: { suggestions: TrainingSuggestion[] }) {
  if (suggestions.length === 0) return <p className="m-0 px-4 pb-4 text-secondary">{TRAINING_TEXT.noSuggestions}</p>;
  return (
    <ul className="m-0 flex list-none flex-col p-0">
      {suggestions.map((suggestion) => (
        <li key={suggestion.key} className="flex flex-col gap-1.5 border-t border-hairline px-4 py-3.5">
          <span className="flex flex-wrap items-center gap-2.5">
            <span className="text-body font-medium text-label">{suggestion.title}</span>
            <CodeChange
              before={suggestion.code_before}
              after={suggestion.code_after}
              addedLabel={TRAINING_TEXT.added}
              changedLabel={TRAINING_TEXT.changed}
            />
          </span>
          {suggestion.reasoning ? <p className="m-0 text-subhead text-secondary">{suggestion.reasoning}</p> : null}
          {suggestion.evidence.length > 0 ? (
            <ul aria-label={TRAINING_TEXT.evidenceLabel} className="m-0 flex list-none flex-col gap-1 p-0">
              {suggestion.evidence.map((quote) => (
                <li key={quote} className="border-l-2 border-separator pl-2.5 text-subhead text-label-soft">
                  {quote}
                </li>
              ))}
            </ul>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

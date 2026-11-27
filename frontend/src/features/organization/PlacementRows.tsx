import { useId } from "react";
import { Select } from "@/components/ui/Select";
import type { OrganizationPracticeRow, PracticeRole } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { PRACTICE_ROLES } from "@/lib/roles";
import { ORGANIZATION_TEXT } from "./strings";

export const NOT_ADDED = "none";

export type PlacementChoice = PracticeRole | typeof NOT_ADDED;

interface PlacementRowsProps {
  practices: readonly Pick<OrganizationPracticeRow, "id" | "name">[];
  choices: Record<string, PlacementChoice>;
  error: string | null;
  onChange: (practiceId: string, choice: PlacementChoice) => void;
}

const words = ORGANIZATION_TEXT.person;
const OPTIONS = [
  { value: NOT_ADDED, label: words.notAdded },
  ...PRACTICE_ROLES.map((role) => ({ value: role, label: ROLE_LABELS[role] })),
] as { value: PlacementChoice; label: string }[];

export function PlacementRows({ practices, choices, error, onChange }: PlacementRowsProps) {
  const errorId = useId();
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0" aria-describedby={error ? errorId : undefined}>
      <legend className="mb-1 text-subhead font-medium text-label">{words.practicesLabel}</legend>
      {practices.map((practice) => (
        <div key={practice.id} className="flex flex-wrap items-center justify-between gap-3">
          <span className="min-w-0 text-body text-label">{practice.name}</span>
          <Select
            variant="filter"
            label={words.roleIn(practice.name)}
            value={choices[practice.id] ?? NOT_ADDED}
            options={OPTIONS}
            onChange={(choice) => onChange(practice.id, choice)}
          />
        </div>
      ))}
      {error ? (
        <span id={errorId} className="text-footnote text-bad-text">
          {error}
        </span>
      ) : null}
    </fieldset>
  );
}

export function chosenPlacements(choices: Record<string, PlacementChoice>): { practice_id: string; role: PracticeRole }[] {
  return Object.entries(choices).flatMap(([practiceId, choice]) =>
    choice === NOT_ADDED ? [] : [{ practice_id: practiceId, role: choice }],
  );
}

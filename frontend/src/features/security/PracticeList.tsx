import { PRACTICE_TEXT } from "@/components/shared/practices/strings";
import { Button } from "@/components/ui/Button";
import type { PracticeChoice } from "@/lib/api/types";
import { ROLE_LABELS } from "@/lib/labels";
import { SECURITY_TEXT } from "./strings";

interface PracticeListProps {
  practices: PracticeChoice[];
  currentId: string | null;
  onLeave: (practice: PracticeChoice) => void;
}

export function PracticeList({ practices, currentId, onLeave }: PracticeListProps) {
  const words = SECURITY_TEXT.practices;
  return (
    <ul aria-label={words.listLabel} className="m-0 list-none p-0">
      {practices.map((practice) => (
        <li
          key={practice.id}
          className="flex min-h-13 items-center justify-between gap-4 border-t border-hairline px-4.5 py-2 text-body"
        >
          <span className="flex min-w-0 flex-col">
            <span className="truncate">{practice.name}</span>
            <span className="text-footnote text-secondary">
              {practice.id === currentId ? words.current(ROLE_LABELS[practice.role]) : ROLE_LABELS[practice.role]}
            </span>
          </span>
          <Button size="sm" variant="plain" aria-label={PRACTICE_TEXT.leaveFor(practice.name)} onClick={() => onLeave(practice)}>
            {PRACTICE_TEXT.leave}
          </Button>
        </li>
      ))}
    </ul>
  );
}

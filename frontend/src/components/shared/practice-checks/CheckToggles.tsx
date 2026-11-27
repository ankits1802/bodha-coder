import { Toggle } from "@/components/ui/Toggle";
import type { CheckKey, Checks } from "@/lib/api/types";
import { CHECK_ORDER } from "./checkList";
import { CHECK_TEXT } from "./strings";

interface CheckTogglesProps {
  checks: Checks;
  onChange: (key: CheckKey, on: boolean) => void;
}

export function CheckToggles({ checks, onChange }: CheckTogglesProps) {
  return (
    <ul className="m-0 list-none p-0">
      {CHECK_ORDER.map((key) => (
        <li key={key} className="flex h-12 items-center justify-between gap-3 border-t border-hairline px-4 text-body">
          <span aria-hidden="true">{CHECK_TEXT.labels[key]}</span>
          <Toggle label={CHECK_TEXT.labels[key]} checked={checks[key] ?? false} onChange={(on) => onChange(key, on)} />
        </li>
      ))}
    </ul>
  );
}

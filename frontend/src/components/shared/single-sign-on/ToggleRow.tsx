import type { ReactNode } from "react";
import { Toggle } from "@/components/ui/Toggle";

interface ToggleRowProps {
  label: string;
  toggleLabel?: string;
  checked: boolean;
  disabled?: boolean;
  detail?: ReactNode;
  onChange: (checked: boolean) => void;
}

export function ToggleRow({ label, toggleLabel, checked, disabled = false, detail, onChange }: ToggleRowProps) {
  return (
    <div className="flex min-h-11 items-center justify-between gap-3 text-body">
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="break-all">{label}</span>
        {detail}
      </span>
      <Toggle label={toggleLabel ?? label} checked={checked} disabled={disabled} onChange={onChange} />
    </div>
  );
}

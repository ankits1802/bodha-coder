import { CheckMark } from "../CheckMark";
import { ToneDot } from "../StatusDot";
import type { SelectOption } from "./selectModel";

interface SelectOptionRowProps {
  id: string;
  option: SelectOption;
  selected: boolean;
  active: boolean;
  onHover: () => void;
  onChoose: () => void;
}

export function SelectOptionRow({ id, option, selected, active, onHover, onChoose }: SelectOptionRowProps) {
  const disabled = Boolean(option.disabled);
  const tone = disabled ? "cursor-default text-tertiary" : "cursor-pointer text-label";
  return (
    <div
      id={id}
      role="option"
      aria-selected={selected}
      aria-disabled={disabled || undefined}
      onMouseDown={(event) => event.preventDefault()}
      onMouseMove={disabled ? undefined : onHover}
      onClick={disabled ? undefined : onChoose}
      className={`flex min-h-8.5 items-center gap-2 py-1.5 pr-4 pl-2.5 text-body whitespace-nowrap ${active ? "bg-fill-plain-hover" : ""} ${tone}`}
    >
      <CheckMark className={`flex-none ${selected ? "" : "invisible"}`} />
      {option.tone ? <ToneDot tone={option.tone} /> : null}
      <span className="truncate">{option.label}</span>
    </div>
  );
}

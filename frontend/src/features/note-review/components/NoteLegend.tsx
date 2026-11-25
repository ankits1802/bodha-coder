import { StatusDot } from "@/components/ui/StatusDot";
import { REVIEW_TEXT } from "../strings";

export function NoteLegend() {
  const words = REVIEW_TEXT.legend;
  return (
    <div className="flex flex-wrap gap-3.5">
      <StatusDot tone="ok">{words.ok}</StatusDot>
      <StatusDot tone="warn">{words.warn}</StatusDot>
      <StatusDot tone="bad">{words.bad}</StatusDot>
    </div>
  );
}

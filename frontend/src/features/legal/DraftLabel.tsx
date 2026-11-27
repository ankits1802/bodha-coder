import { StatusDot } from "@/components/ui/StatusDot";
import { LEGAL_TEXT } from "./strings";

export function DraftLabel() {
  return (
    <p className="m-0">
      <span className="inline-flex rounded-full bg-warn-surface px-3 py-1 print:border print:border-label">
        <StatusDot tone="warn" className="font-semibold">
          {LEGAL_TEXT.draft}
        </StatusDot>
      </span>
    </p>
  );
}

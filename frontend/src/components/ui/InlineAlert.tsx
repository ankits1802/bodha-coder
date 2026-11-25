import type { ReactNode } from "react";
import type { StatusTone } from "./StatusDot";

interface InlineAlertProps {
  tone: Extract<StatusTone, "ok" | "warn" | "bad">;
  children: ReactNode;
  action?: ReactNode;
}

const DOTS = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad" } as const;

export function InlineAlert({ tone, children, action }: InlineAlertProps) {
  return (
    <div
      role={tone === "bad" ? "alert" : "status"}
      className={`flex flex-wrap items-center justify-between gap-3 rounded-field px-3.5 py-2.5 text-subhead ${tone === "warn" ? "bg-warn-surface" : "bg-muted-panel"}`}
    >
      <span className="flex items-center gap-2 text-label">
        <span aria-hidden="true" className={`size-2 flex-none rounded-full ${DOTS[tone]}`} />
        {children}
      </span>
      {action}
    </div>
  );
}

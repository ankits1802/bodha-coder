import type { ReactNode } from "react";

export type StatusTone = "ok" | "warn" | "bad" | "low" | "dark" | "neutral";

const DOTS: Record<StatusTone, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  bad: "bg-bad",
  low: "bg-low",
  dark: "bg-dark",
  neutral: "bg-neutral",
};

interface StatusDotProps {
  tone: StatusTone;
  children: ReactNode;
  className?: string;
}

export function StatusDot({ tone, children, className = "" }: StatusDotProps) {
  return (
    <span className={`inline-flex items-center gap-1.75 text-subhead whitespace-nowrap text-label-soft ${className}`}>
      <span aria-hidden="true" className={`size-2 flex-none rounded-full ${DOTS[tone]}`} />
      {children}
    </span>
  );
}

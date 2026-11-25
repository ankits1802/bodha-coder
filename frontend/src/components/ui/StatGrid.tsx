import type { ReactNode } from "react";

interface StatGridProps {
  label: string;
  children: ReactNode;
}

export function StatGrid({ label, children }: StatGridProps) {
  return (
    <section
      aria-label={label}
      className="grid grid-cols-[repeat(auto-fit,minmax(10rem,1fr))] overflow-hidden rounded-panel bg-surface shadow-panel"
    >
      {children}
    </section>
  );
}

interface StatCellProps {
  label: ReactNode;
  value: ReactNode;
  note?: ReactNode;
}

export function StatCell({ label, value, note }: StatCellProps) {
  return (
    <div className="-ml-px flex flex-col gap-1 border-l border-hairline px-5 py-4.5">
      <span className="text-footnote text-secondary">{label}</span>
      <span className="text-stat font-semibold tracking-title tabular-nums">{value}</span>
      {note ? <span className="text-footnote text-secondary">{note}</span> : null}
    </div>
  );
}

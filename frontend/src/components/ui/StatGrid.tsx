"use client";

import Link from "next/link";
import { createContext, useContext, type ReactNode } from "react";
import { StatusDot, type StatusTone } from "./StatusDot";

export type StatSize = "md" | "lg";

const SIZES: Record<StatSize, { grid: string; gap: string; value: string; note: string }> = {
  md: { grid: "grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]", gap: "gap-1", value: "text-stat", note: "text-footnote" },
  lg: { grid: "grid-cols-[repeat(auto-fit,minmax(11rem,1fr))]", gap: "gap-1.5", value: "text-stat-lg", note: "text-subhead" },
};

const CELL = "-ml-px flex flex-col border-l border-hairline px-5 py-4.5";
const LINKED = "hover:bg-row-hover focus-visible:-outline-offset-2";
const PAUSE = ", ";

const StatSizeContext = createContext<StatSize>("md");

interface StatGridProps {
  label: string;
  size?: StatSize;
  children: ReactNode;
}

export function StatGrid({ label, size = "md", children }: StatGridProps) {
  return (
    <section aria-label={label} className={`grid ${SIZES[size].grid} overflow-hidden rounded-panel bg-surface shadow-panel`}>
      <StatSizeContext.Provider value={size}>{children}</StatSizeContext.Provider>
    </section>
  );
}

interface StatFacts {
  label: string;
  tone?: StatusTone;
}

type StatCellProps = StatFacts &
  ({ value: ReactNode; note?: ReactNode; href?: undefined } | { value: string; note?: string; href: string | null });

function StatLabel({ label, tone }: { label: string; tone?: StatusTone }) {
  if (tone) return <StatusDot tone={tone}>{label}</StatusDot>;
  return <span className="text-footnote text-secondary">{label}</span>;
}

export function StatCell(props: StatCellProps) {
  const sized = SIZES[useContext(StatSizeContext)];
  const body = (
    <>
      <StatLabel label={props.label} tone={props.tone} />
      <span className={`${sized.value} font-semibold tracking-title tabular-nums`}>{props.value}</span>
      {props.note ? <span className={`${sized.note} text-secondary`}>{props.note}</span> : null}
    </>
  );
  if (props.href == null) return <div className={`${CELL} ${sized.gap}`}>{body}</div>;
  const name = [props.label, props.value, props.note].filter(Boolean).join(PAUSE);
  return (
    <Link href={props.href} aria-label={name} className={`${CELL} ${sized.gap} ${LINKED}`}>
      {body}
    </Link>
  );
}

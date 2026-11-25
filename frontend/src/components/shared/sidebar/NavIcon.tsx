import type { ReactNode } from "react";

export type NavIconName = "calendar" | "upload" | "list" | "shield" | "card" | "bars" | "house" | "people" | "lock" | "gauge" | "clock";

const STROKE = { fill: "none", stroke: "currentColor", strokeWidth: 1.3, strokeLinecap: "round", strokeLinejoin: "round" } as const;

const PATHS: Record<NavIconName, ReactNode> = {
  calendar: (
    <>
      <rect x="2" y="3" width="12" height="11" rx="2.5" {...STROKE} />
      <path d="M2 6.5h12M5.5 1.8v2.4M10.5 1.8v2.4" {...STROKE} />
    </>
  ),
  upload: <path d="M8 10.5V2.5M5 5.3L8 2.3l3 3M2.5 10v2.2c0 .7.6 1.3 1.3 1.3h8.4c.7 0 1.3-.6 1.3-1.3V10" {...STROKE} />,
  list: (
    <>
      <path d="M5.5 4h8M5.5 8h8M5.5 12h8" {...STROKE} />
      <circle cx="2.6" cy="4" r=".9" fill="currentColor" />
      <circle cx="2.6" cy="8" r=".9" fill="currentColor" />
      <circle cx="2.6" cy="12" r=".9" fill="currentColor" />
    </>
  ),
  shield: <path d="M8 1.8l5 2v4c0 3-2.1 5.3-5 6.4-2.9-1.1-5-3.4-5-6.4v-4z" {...STROKE} />,
  card: (
    <>
      <rect x="1.8" y="3.5" width="12.4" height="9" rx="2" {...STROKE} />
      <path d="M1.8 6.5h12.4" {...STROKE} />
    </>
  ),
  bars: <path d="M3 13.5V9M6.3 13.5V4.5M9.7 13.5V7.5M13 13.5V2.5" {...STROKE} strokeWidth={1.5} />,
  house: (
    <>
      <path d="M2.5 13.5V6.8L8 2.5l5.5 4.3v6.7z" {...STROKE} />
      <path d="M6.5 13.5v-3.5h3v3.5" {...STROKE} />
    </>
  ),
  people: (
    <>
      <circle cx="6" cy="5.5" r="2.4" {...STROKE} />
      <path d="M1.8 13c.5-2.3 2.1-3.5 4.2-3.5s3.7 1.2 4.2 3.5M10.6 3.3a2.2 2.2 0 0 1 0 4.3M11.8 9.6c1.3.4 2.1 1.5 2.4 3.4" {...STROKE} />
    </>
  ),
  lock: (
    <>
      <rect x="3" y="7" width="10" height="7" rx="1.8" {...STROKE} />
      <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" {...STROKE} />
    </>
  ),
  gauge: (
    <>
      <path d="M2.5 11a5.5 5.5 0 1 1 11 0" {...STROKE} />
      <path d="M8 11l2.6-3" {...STROKE} strokeWidth={1.5} />
    </>
  ),
  clock: (
    <>
      <circle cx="8" cy="8" r="6" {...STROKE} />
      <path d="M8 4.8V8l2.2 1.4" {...STROKE} />
    </>
  ),
};

export function NavIcon({ name }: { name: NavIconName }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="flex-none text-secondary">
      {PATHS[name]}
    </svg>
  );
}

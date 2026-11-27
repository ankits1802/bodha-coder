import type { ReactNode } from "react";

export type FlowStep = "upload" | "read" | "ask" | "approve" | "export" | "remit";

const PATHS: Record<FlowStep, ReactNode> = {
  upload: (
    <>
      <path d="M12 15V4.5M7.8 8.7 12 4.5l4.2 4.2" />
      <path d="M4.5 14v4a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-4" />
    </>
  ),
  read: (
    <>
      <path d="M6.5 3.5h7.5l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 19V5a1.5 1.5 0 0 1 1.5-1.5Z" />
      <path d="M13.5 3.5V8h4.5M8.5 12h7M8.5 15.5h5" />
    </>
  ),
  ask: (
    <>
      <path d="M5.5 4.5h13A1.5 1.5 0 0 1 20 6v9a1.5 1.5 0 0 1-1.5 1.5h-7l-4.5 3.5v-3.5H5.5A1.5 1.5 0 0 1 4 15V6a1.5 1.5 0 0 1 1.5-1.5Z" />
      <path d="M10 9a2 2 0 1 1 2.9 1.8c-.6.3-.9.8-.9 1.4M12 14.3v.1" />
    </>
  ),
  approve: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.3 12.3 2.5 2.5 5-5.4" />
    </>
  ),
  export: (
    <>
      <path d="M14 4h6v6M20 4l-8.5 8.5" />
      <path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10" />
    </>
  ),
  remit: (
    <>
      <path d="M4.5 12a7.5 7.5 0 0 1 12.9-5.2L19.5 9M19.5 4.5V9H15" />
      <path d="M19.5 12a7.5 7.5 0 0 1-12.9 5.2L4.5 15M4.5 19.5V15H9" />
    </>
  ),
};

export function FlowIcon({ step, className }: { step: FlowStep; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className}>
      {PATHS[step]}
    </svg>
  );
}

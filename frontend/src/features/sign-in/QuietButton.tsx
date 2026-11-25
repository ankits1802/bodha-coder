import type { ReactNode } from "react";

interface QuietButtonProps {
  onClick: () => void;
  children: ReactNode;
}

export const QUIET_LINK =
  "cursor-pointer self-center rounded-control border-0 bg-transparent px-2 py-1 text-body text-secondary hover:text-label";

export function QuietButton({ onClick, children }: QuietButtonProps) {
  return (
    <button type="button" onClick={onClick} className={QUIET_LINK}>
      {children}
    </button>
  );
}

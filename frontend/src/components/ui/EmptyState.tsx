import type { ReactNode } from "react";

interface EmptyStateProps {
  title: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <p className="m-0 text-body-lg text-secondary">{title}</p>
      {action}
    </div>
  );
}

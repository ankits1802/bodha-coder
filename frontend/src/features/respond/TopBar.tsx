import { SHARED_TEXT } from "@/components/shared/strings";
import { Avatar } from "@/components/ui/Avatar";

interface TopBarProps {
  practiceName?: string;
  providerName?: string;
}

export function TopBar({ practiceName, providerName }: TopBarProps) {
  return (
    <div className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-separator bg-surface px-4 sm:px-7">
      <span className="flex items-baseline gap-3.5">
        <span className="text-body-lg font-semibold tracking-snug">{SHARED_TEXT.brand}</span>
        {practiceName ? <span className="text-subhead text-secondary">{practiceName}</span> : null}
      </span>
      {providerName ? (
        <span className="flex items-center gap-2.5">
          <span className="text-subhead">{providerName}</span>
          <Avatar name={providerName} />
        </span>
      ) : null}
    </div>
  );
}

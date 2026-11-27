"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { usePlanStatus } from "@/hooks/usePlanStatus";
import { localIsoDate } from "@/lib/dates";
import type { Role } from "@/lib/api/types";
import { PLAN_PATH, bannerFor, readDismissal, saveDismissal } from "./bannerModel";
import { PLAN_BANNER_TEXT } from "./strings";

export function PlanBanner({ role }: { role: Role }) {
  const pathname = usePathname();
  const admin = role === "admin";
  const remote = usePlanStatus(admin);
  const [dismissedOn, setDismissedOn] = useState<string | null>(() => (admin ? readDismissal() : null));
  const today = localIsoDate();
  const view = remote.state.status === "success" ? bannerFor(remote.state.data) : null;
  if (!view || dismissedOn === today || pathname === PLAN_PATH) return null;

  function dismiss(): void {
    saveDismissal(today);
    setDismissedOn(today);
  }

  return (
    <InlineAlert
      tone={view.tone}
      action={
        <span className="flex items-center gap-4">
          <Link href={PLAN_PATH} className="font-medium text-label underline underline-offset-2">
            {view.action}
          </Link>
          <button type="button" onClick={dismiss} className="cursor-pointer text-secondary hover:text-label">
            {PLAN_BANNER_TEXT.dismiss}
          </button>
        </span>
      }
    >
      {view.text}
    </InlineAlert>
  );
}

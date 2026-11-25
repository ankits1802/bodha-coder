"use client";

import type { ReactNode } from "react";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { canUse, homeFor, type Area } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { SHARED_TEXT } from "./strings";

interface AreaGuardProps {
  area: Area;
  children: ReactNode;
}

export function AreaGuard({ area, children }: AreaGuardProps) {
  const { user } = useSession();
  if (user && canUse(user.role, area)) return <>{children}</>;
  return (
    <EmptyState
      title={SHARED_TEXT.notAllowed}
      action={
        user ? (
          <ButtonLink href={homeFor(user.role)} size="sm">
            {SHARED_TEXT.goHome}
          </ButtonLink>
        ) : null
      }
    />
  );
}

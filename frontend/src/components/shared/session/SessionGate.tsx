"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { endSession, refreshSession } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { homeFor } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { SHARED_TEXT } from "../strings";
import { useIdleSignOut } from "./useIdleSignOut";

export type SessionScope = "practice" | "hq";

interface SessionGateProps {
  scope: SessionScope;
  children: ReactNode;
}

export function SessionGate({ scope, children }: SessionGateProps) {
  const { user } = useSession();
  const router = useRouter();
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const inScope = user !== null && (user.role === "hq") === (scope === "hq");

  useEffect(() => {
    if (user) return;
    let live = true;
    refreshSession().then(
      (ok) => {
        if (live && !ok) endSession();
      },
      (error: unknown) => {
        if (live) setFailure(messageOf(error));
      },
    );
    return () => {
      live = false;
    };
  }, [user, attempt]);

  useEffect(() => {
    if (user && !inScope) router.replace(homeFor(user.role));
  }, [user, inScope, router]);

  useIdleSignOut(user);

  if (failure) {
    const retry = () => {
      setFailure(null);
      setAttempt((value) => value + 1);
    };
    return <ErrorState message={failure} retryLabel={SHARED_TEXT.retry} onRetry={retry} />;
  }
  if (!inScope) return <LoadingState label={SHARED_TEXT.loading} />;
  return <>{children}</>;
}

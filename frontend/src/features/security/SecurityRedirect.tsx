"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { useSession } from "@/lib/session/useSession";
import { securityDestination } from "./securityDestination";
import { SECURITY_TEXT } from "./strings";

export function SecurityRedirect() {
  const { user } = useSession();
  const router = useRouter();
  const search = useSearchParams().toString();

  useEffect(() => {
    if (user) router.replace(securityDestination(user, search));
  }, [user, search, router]);

  return <LoadingState label={SECURITY_TEXT.loading} />;
}

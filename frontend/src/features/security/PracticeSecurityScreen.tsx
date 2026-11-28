"use client";

import { SingleSignOn } from "@/components/shared/single-sign-on/SingleSignOn";
import { PageHeader } from "@/components/ui/PageHeader";
import { PRACTICE_DOMAINS } from "@/lib/api/domains";
import { useSession } from "@/lib/session/useSession";
import { SecuritySettingsPanel } from "./SecuritySettingsPanel";
import { SECURITY_TEXT } from "./strings";

export function PracticeSecurityScreen() {
  const { user } = useSession();
  return (
    <>
      <PageHeader title={SECURITY_TEXT.title} />
      <SecuritySettingsPanel />
      {user?.role === "admin" ? <SingleSignOn scope={PRACTICE_DOMAINS} /> : null}
    </>
  );
}

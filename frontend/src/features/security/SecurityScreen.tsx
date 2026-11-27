"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useSession } from "@/lib/session/useSession";
import { DevicesPanel } from "./DevicesPanel";
import { DigestPreferencePanel } from "./DigestPreferencePanel";
import { PracticesPanel } from "./PracticesPanel";
import { RecoveryCodesPanel } from "./RecoveryCodesPanel";
import { SECURITY_TEXT } from "./strings";

export function SecurityScreen() {
  const { user } = useSession();
  return (
    <>
      <PageHeader title={SECURITY_TEXT.accountTitle} />
      {user ? <PracticesPanel user={user} /> : null}
      <DevicesPanel />
      <RecoveryCodesPanel />
      <DigestPreferencePanel />
    </>
  );
}

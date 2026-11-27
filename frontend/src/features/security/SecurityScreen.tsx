"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { canDo } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { AccessLogPanel } from "./AccessLogPanel";
import { DevicesPanel } from "./DevicesPanel";
import { DigestPreferencePanel } from "./DigestPreferencePanel";
import { PracticesPanel } from "./PracticesPanel";
import { RecoveryCodesPanel } from "./RecoveryCodesPanel";
import { SecuritySettingsPanel } from "./SecuritySettingsPanel";
import { SECURITY_TEXT } from "./strings";

export function SecurityScreen() {
  const { user } = useSession();
  const managesPractice = canDo(user?.role, "manageSecurity");
  return (
    <>
      <PageHeader title={SECURITY_TEXT.title} />
      {managesPractice ? <SecuritySettingsPanel /> : null}
      {user ? <PracticesPanel user={user} /> : null}
      <DevicesPanel />
      <RecoveryCodesPanel />
      <DigestPreferencePanel />
      {managesPractice ? <AccessLogPanel /> : null}
    </>
  );
}

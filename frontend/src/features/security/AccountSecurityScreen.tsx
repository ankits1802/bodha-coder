"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { DevicesPanel } from "./DevicesPanel";
import { RecoveryCodesPanel } from "./RecoveryCodesPanel";
import { SECURITY_TEXT } from "./strings";

export function AccountSecurityScreen() {
  return (
    <>
      <PageHeader title={SECURITY_TEXT.title} />
      <DevicesPanel />
      <RecoveryCodesPanel />
    </>
  );
}

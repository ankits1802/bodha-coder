"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SecuritySettingsPanel } from "./SecuritySettingsPanel";
import { SECURITY_TEXT } from "./strings";

export function PracticeSecurityScreen() {
  return (
    <>
      <PageHeader title={SECURITY_TEXT.title} />
      <SecuritySettingsPanel />
    </>
  );
}

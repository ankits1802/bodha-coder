"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { AccessLogPanel } from "./AccessLogPanel";
import { SECURITY_TEXT } from "./strings";

export function AccessLogScreen() {
  return (
    <>
      <PageHeader title={SECURITY_TEXT.log.title} />
      <AccessLogPanel />
    </>
  );
}

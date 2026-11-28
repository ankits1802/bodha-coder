"use client";

import { useMemo } from "react";
import { SingleSignOn } from "@/components/shared/single-sign-on/SingleSignOn";
import { PageHeader } from "@/components/ui/PageHeader";
import type { DomainScope } from "@/lib/api/domains";
import { ORGANIZATION_TEXT } from "./strings";

export function OrganizationSignInScreen({ organizationId }: { organizationId: string }) {
  const scope = useMemo<DomainScope>(() => ({ kind: "organization", organizationId }), [organizationId]);
  return (
    <>
      <PageHeader title={ORGANIZATION_TEXT.signIn.title} />
      <SingleSignOn scope={scope} />
    </>
  );
}

"use client";

import { useMemo } from "react";
import { DomainClaims } from "@/components/shared/domain-claims/DomainClaims";
import { PageHeader } from "@/components/ui/PageHeader";
import { RemoteView } from "@/components/ui/RemoteView";
import type { DomainScope } from "@/lib/api/domains";
import { ORGANIZATION_TEXT } from "./strings";
import { useOrganization } from "./useOrganizationData";

const TEXT = { loading: ORGANIZATION_TEXT.loading, empty: ORGANIZATION_TEXT.practices.empty, retry: ORGANIZATION_TEXT.retry };

export function OrganizationDomainsScreen({ organizationId }: { organizationId: string }) {
  const remote = useOrganization(organizationId);
  const scope = useMemo<DomainScope>(() => ({ kind: "organization", organizationId }), [organizationId]);
  return (
    <>
      <PageHeader title={ORGANIZATION_TEXT.domains.title} />
      <RemoteView state={remote.state} text={TEXT} isEmpty={(data) => data.practices.length === 0} onRetry={remote.reload}>
        {(data) => (
          <DomainClaims
            scope={scope}
            practices={data.practices.filter((practice) => practice.open).map(({ id, name }) => ({ id, name }))}
          />
        )}
      </RemoteView>
    </>
  );
}

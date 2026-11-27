import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { OrganizationDomainsScreen } from "@/features/organization/OrganizationDomainsScreen";
import { ORGANIZATION_TEXT } from "@/features/organization/strings";

export const metadata: Metadata = { title: ORGANIZATION_TEXT.domains.title };

export default async function OrganizationDomainsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={ORGANIZATION_TEXT.loading} />}>
      <OrganizationDomainsScreen organizationId={id} />
    </Suspense>
  );
}

import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { OrganizationInsightsScreen } from "@/features/organization/OrganizationInsightsScreen";
import { ORGANIZATION_TEXT } from "@/features/organization/strings";

export const metadata: Metadata = { title: ORGANIZATION_TEXT.insights.title };

export default async function OrganizationInsightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={ORGANIZATION_TEXT.insights.loading} />}>
      <OrganizationInsightsScreen organizationId={id} />
    </Suspense>
  );
}

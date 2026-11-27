import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { OrganizationPlanScreen } from "@/features/organization/OrganizationPlanScreen";
import { ORGANIZATION_TEXT } from "@/features/organization/strings";

export const metadata: Metadata = { title: ORGANIZATION_TEXT.plan.title };

export default async function OrganizationPlanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={ORGANIZATION_TEXT.plan.loading} />}>
      <OrganizationPlanScreen organizationId={id} />
    </Suspense>
  );
}

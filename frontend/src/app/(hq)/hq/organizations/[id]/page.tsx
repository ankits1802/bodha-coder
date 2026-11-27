import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqOrganizationScreen } from "@/features/hq/organization/HqOrganizationScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.organization.title };

export default async function HqOrganizationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.organization.loading} />}>
      <HqOrganizationScreen organizationId={id} />
    </Suspense>
  );
}

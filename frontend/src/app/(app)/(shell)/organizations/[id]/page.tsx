import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { OrganizationPracticesScreen } from "@/features/organization/OrganizationPracticesScreen";
import { ORGANIZATION_TEXT } from "@/features/organization/strings";

export const metadata: Metadata = { title: ORGANIZATION_TEXT.practices.title };

export default async function OrganizationPracticesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={ORGANIZATION_TEXT.loading} />}>
      <OrganizationPracticesScreen organizationId={id} />
    </Suspense>
  );
}

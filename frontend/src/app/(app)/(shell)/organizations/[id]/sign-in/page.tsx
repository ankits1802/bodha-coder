import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { OrganizationSignInScreen } from "@/features/organization/OrganizationSignInScreen";
import { ORGANIZATION_TEXT } from "@/features/organization/strings";

export const metadata: Metadata = { title: ORGANIZATION_TEXT.signIn.title };

export default async function OrganizationSignInPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label={ORGANIZATION_TEXT.loading} />}>
      <OrganizationSignInScreen organizationId={id} />
    </Suspense>
  );
}

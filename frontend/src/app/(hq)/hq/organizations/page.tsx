import type { Metadata } from "next";
import { Suspense } from "react";
import { LoadingState } from "@/components/ui/LoadingState";
import { HqOrganizationsScreen } from "@/features/hq/organizations/HqOrganizationsScreen";
import { HQ_TEXT } from "@/features/hq/strings";

export const metadata: Metadata = { title: HQ_TEXT.organizations.title };

export default function HqOrganizationsPage() {
  return (
    <Suspense fallback={<LoadingState label={HQ_TEXT.organizations.loading} />}>
      <HqOrganizationsScreen />
    </Suspense>
  );
}

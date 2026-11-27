"use client";

import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { SHARED_TEXT } from "@/components/shared/strings";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { Tabs } from "@/components/ui/Tabs";
import { organizationPath } from "@/lib/paths";
import { homeFor } from "@/lib/roles";
import { useSession } from "@/lib/session/useSession";
import { ORGANIZATION_TEXT, type OrganizationTabKey } from "./strings";

interface OrganizationAreaProps {
  organizationId: string;
  children: ReactNode;
}

const TAB_KEYS: readonly OrganizationTabKey[] = ["practices", "insights", "plan", "domains"];

function tabPath(organizationId: string, key: OrganizationTabKey): string {
  return key === "practices" ? organizationPath(organizationId) : organizationPath(organizationId, key);
}

function tabAt(organizationId: string, pathname: string): OrganizationTabKey {
  return TAB_KEYS.find((key) => key !== "practices" && pathname.startsWith(tabPath(organizationId, key))) ?? "practices";
}

export function OrganizationArea({ organizationId, children }: OrganizationAreaProps) {
  const { user } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const organization = user?.organizations?.find((choice) => choice.id === organizationId);
  if (!user || !organization) {
    const home = user ? (
      <ButtonLink href={homeFor(user)} size="sm">
        {SHARED_TEXT.goHome}
      </ButtonLink>
    ) : null;
    return <EmptyState title={ORGANIZATION_TEXT.notAllowed} action={home} />;
  }
  if (user.billing_only) return <div className="flex flex-col gap-6">{children}</div>;
  const current = tabAt(organizationId, pathname);
  return (
    <Tabs
      label={organization.name}
      tabs={TAB_KEYS.map((key) => ({ value: key, label: ORGANIZATION_TEXT.tabs[key] }))}
      value={current}
      activation="manual"
      onChange={(key) => {
        if (key !== current) router.push(tabPath(organizationId, key));
      }}
      panelClassName="flex flex-col gap-6"
    >
      {children}
    </Tabs>
  );
}

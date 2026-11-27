import type { ReactNode } from "react";
import { OrganizationArea } from "@/features/organization/OrganizationArea";

interface OrganizationLayoutProps {
  children: ReactNode;
  params: Promise<{ id: string }>;
}

export default async function OrganizationLayout({ children, params }: OrganizationLayoutProps) {
  const { id } = await params;
  return <OrganizationArea organizationId={id}>{children}</OrganizationArea>;
}

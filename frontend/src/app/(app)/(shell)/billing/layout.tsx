import type { ReactNode } from "react";
import { AreaTabs } from "@/components/shared/sidebar/AreaTabs";

export default function BillingLayout({ children }: { children: ReactNode }) {
  return <AreaTabs navKey="billing">{children}</AreaTabs>;
}

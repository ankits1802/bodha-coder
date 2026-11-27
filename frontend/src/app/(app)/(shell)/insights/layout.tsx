import type { ReactNode } from "react";
import { AreaTabs } from "@/components/shared/sidebar/AreaTabs";

export default function InsightsLayout({ children }: { children: ReactNode }) {
  return <AreaTabs navKey="insights">{children}</AreaTabs>;
}

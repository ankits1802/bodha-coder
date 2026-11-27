import type { ReactNode } from "react";
import { AreaTabs } from "@/components/shared/sidebar/AreaTabs";

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return <AreaTabs navKey="settings">{children}</AreaTabs>;
}

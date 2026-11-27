"use client";

import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { useSession } from "@/lib/session/useSession";
import { activeTab, navItemFor } from "./navItems";

interface AreaTabsProps {
  navKey: string;
  children: ReactNode;
}

export function AreaTabs({ navKey, children }: AreaTabsProps) {
  const { user } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const item = user ? navItemFor(user, navKey) : null;
  const tabs = item?.tabs ?? [];
  const current = activeTab(tabs, pathname);
  if (!item || !current || tabs.length < 2) return <>{children}</>;

  return (
    <Tabs
      label={item.label}
      tabs={tabs.map((tab) => ({ value: tab.key, label: tab.label }))}
      value={current.key}
      activation="manual"
      onChange={(key) => {
        const chosen = tabs.find((tab) => tab.key === key);
        if (chosen && chosen.key !== current.key) router.push(chosen.href);
      }}
      panelClassName="flex flex-col gap-6"
    >
      {children}
    </Tabs>
  );
}

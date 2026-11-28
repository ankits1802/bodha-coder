import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppearanceSync } from "@/components/shared/appearance/AppearanceSync";
import { SessionGate } from "@/components/shared/session/SessionGate";
import { AppShell } from "@/components/shared/sidebar/AppShell";
import { HqSearchPalette } from "@/features/hq/search/HqSearchPalette";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function HqLayout({ children }: { children: ReactNode }) {
  return (
    <SessionGate scope="hq">
      <AppShell>{children}</AppShell>
      <AppearanceSync />
      <HqSearchPalette />
    </SessionGate>
  );
}

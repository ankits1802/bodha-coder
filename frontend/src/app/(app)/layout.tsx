import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppearanceSync } from "@/components/shared/appearance/AppearanceSync";
import { SessionGate } from "@/components/shared/session/SessionGate";
import { ShortcutsDialog } from "@/components/shared/shortcuts/ShortcutsDialog";
import { ToastHost } from "@/components/shared/toast/ToastHost";
import { UsageCapture } from "@/components/shared/usage/UsageCapture";
import { SearchPalette } from "@/features/search/SearchPalette";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function PracticeLayout({ children }: { children: ReactNode }) {
  return (
    <SessionGate scope="practice">
      {children}
      <AppearanceSync />
      <SearchPalette />
      <ShortcutsDialog />
      <ToastHost />
      <UsageCapture />
    </SessionGate>
  );
}

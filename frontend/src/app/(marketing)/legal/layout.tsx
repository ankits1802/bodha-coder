import type { ReactNode } from "react";
import { LegalShell } from "@/features/legal/LegalShell";

export default function LegalLayout({ children }: { children: ReactNode }) {
  return <LegalShell>{children}</LegalShell>;
}

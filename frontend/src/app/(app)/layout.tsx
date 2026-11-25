import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SessionGate } from "@/components/shared/session/SessionGate";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function PracticeLayout({ children }: { children: ReactNode }) {
  return <SessionGate scope="practice">{children}</SessionGate>;
}

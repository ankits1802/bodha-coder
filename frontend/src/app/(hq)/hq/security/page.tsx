import type { Metadata } from "next";
import { AccountSecurityScreen } from "@/features/security/AccountSecurityScreen";
import { SECURITY_TEXT } from "@/features/security/strings";

export const metadata: Metadata = { title: SECURITY_TEXT.title };

export default function HqSecurityPage() {
  return <AccountSecurityScreen />;
}
